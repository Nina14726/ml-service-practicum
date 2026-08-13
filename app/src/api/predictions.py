from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_session, service_error
from src.api.tasks import enqueue_task
from src.models import PredictionTaskORM, UserORM
from src.schemas import AsyncPredictionAccepted, AsyncPredictionRequest, AsyncPredictionResult, PredictionRequest, PredictionResponse, VideoAnalysisRequest
from src.services import run_prediction

router = APIRouter()


@router.post("/predict", response_model=AsyncPredictionAccepted, status_code=202)
def enqueue_prediction(payload: AsyncPredictionRequest, user: UserORM = Depends(get_current_user), session: Session = Depends(get_session)):
    return enqueue_task(session=session, user=user, model_name=payload.model, features=payload.features)


@router.post("/video-analysis", response_model=AsyncPredictionAccepted, status_code=202)
def enqueue_video_analysis(payload: VideoAnalysisRequest, user: UserORM = Depends(get_current_user), session: Session = Depends(get_session)):
    suffix = payload.filename.rsplit(".", 1)[-1].lower() if "." in payload.filename else ""
    if suffix not in {"mp4", "mov", "webm"}:
        raise HTTPException(status_code=400, detail="Supported video formats: MP4, MOV, WebM")
    return enqueue_task(session=session, user=user, model_name="video_analysis", features={"duration_seconds": payload.duration_seconds}, source_name=payload.filename, source_size=payload.size_bytes, source_duration=payload.duration_seconds)


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
