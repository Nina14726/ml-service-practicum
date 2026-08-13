import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_session, service_error
from src.api.tasks import enqueue_task
from src.models import PredictionTaskORM, UserORM
from src.schemas import AsyncPredictionAccepted, AsyncPredictionRequest, AsyncPredictionResult, PredictionRequest, PredictionResponse
from src.services import run_prediction

router = APIRouter()

MAX_VIDEO_SIZE = 100 * 1024 * 1024
UPLOAD_DIR = Path(os.getenv("VIDEO_UPLOAD_DIR", "/app/uploads"))
VIDEO_TYPES = {
    "mp4": {"video/mp4"},
    "mov": {"video/quicktime", "video/mov"},
    "webm": {"video/webm"},
}


@router.post("/predict", response_model=AsyncPredictionAccepted, status_code=202)
def enqueue_prediction(payload: AsyncPredictionRequest, user: UserORM = Depends(get_current_user), session: Session = Depends(get_session)):
    return enqueue_task(session=session, user=user, model_name=payload.model, features=payload.features)


@router.post("/video-analysis", response_model=AsyncPredictionAccepted, status_code=202)
async def enqueue_video_analysis(
    video: UploadFile = File(...),
    duration_seconds: float = Form(..., gt=0, le=60),
    user: UserORM = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    filename = video.filename or "video"
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="Supported video formats: MP4, MOV, WebM")
    if video.content_type and video.content_type not in VIDEO_TYPES[suffix]:
        raise HTTPException(status_code=400, detail="Video MIME type does not match the file format")

    task_id = str(uuid4())
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    video_path = UPLOAD_DIR / f"{task_id}.{suffix}"
    size = 0

    try:
        with video_path.open("wb") as target:
            while chunk := await video.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_VIDEO_SIZE:
                    raise HTTPException(status_code=413, detail="Video size must not exceed 100 MB")
                target.write(chunk)

        if size == 0:
            raise HTTPException(status_code=400, detail="Video file is empty")

        return enqueue_task(
            session=session,
            user=user,
            model_name="video_analysis",
            features={"duration_seconds": duration_seconds},
            source_name=filename,
            source_size=size,
            source_duration=duration_seconds,
            task_id=task_id,
        )
    except Exception:
        video_path.unlink(missing_ok=True)
        raise
    finally:
        await video.close()


@router.get("/predict/{task_id}", response_model=AsyncPredictionResult)
def get_prediction_result(task_id: str, user: UserORM = Depends(get_current_user), session: Session = Depends(get_session)):
    task = session.get(PredictionTaskORM, task_id)
    if task is None or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Prediction task not found")
    return task


@router.get("/web/api/tasks", response_model=list[AsyncPredictionResult])
def web_task_history(user: UserORM = Depends(get_current_user), session: Session = Depends(get_session)):
    statement = select(PredictionTaskORM).where(PredictionTaskORM.user_id == user.id).order_by(PredictionTaskORM.created_at.desc())
    return list(session.scalars(statement))


@router.post("/predict/sync", response_model=PredictionResponse)
def predict_sync(payload: PredictionRequest, user: UserORM = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        request = run_prediction(session, user.id, payload.model_id, payload.data)
    except ValueError as error:
        raise service_error(error) from error
    return PredictionResponse(request_id=request.id, status=request.status, predictions=request.predictions, invalid_data=request.invalid_data, charged_credits=request.charged_credits)
