import json
import os
import time
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class CoreIdeaDNA(BaseModel):
    logline: str
    metaphor: str
    target_action: str
    strategic_task: str


class StoryStructure(BaseModel):
    exposition: str
    incident: str
    resolution: str


class StoryDramaturgy(BaseModel):
    genre: str
    hero_arc: str
    structure: StoryStructure
    context_overlay: str


class SoundDesign(BaseModel):
    music_score: str
    sfx: list[str]
    the_drop: str
    sound_bridge: str


class Composition(BaseModel):
    foreground: str
    middleground: str
    background: str


class BlockingGeometry(BaseModel):
    composition: Composition
    movement_vectors: str
    precise_actions: list[str]


class CinematographySpecs(BaseModel):
    camera_state: str
    angle: str
    optics_lens: str
    focus_depth: str
    fps_speed: str


class Lighting(BaseModel):
    source: str
    quality: str


class ArtDirection(BaseModel):
    palette: str
    visual_rhymes: str
    lighting: Lighting
    key_props: list[str]


class Hooks(BaseModel):
    start_3s: str
    middle_intrigue: str
    end_reward: str


class EditingPsychology(BaseModel):
    pacing_tempo: str
    hooks: Hooks
    diegesis: str
    transitions_matchcuts: str
    emotional_curve: str


class ScriptItem(BaseModel):
    timecode: str
    action: str
    audio: str
    meaning: str


class AnalyticalFilter(BaseModel):
    one_goal_principle: str
    empathy_effort: str
    metaphor_logic: str
    cgi_honesty: str
    drop_off_point: str
    unity_of_focus: str


class MasterBreakdown(BaseModel):
    core_idea_dna: CoreIdeaDNA
    story_dramaturgy: StoryDramaturgy
    sound_design: SoundDesign
    blocking_geometry: BlockingGeometry
    cinematography_specs: CinematographySpecs
    art_direction: ArtDirection
    editing_psychology: EditingPsychology
    script_breakdown: list[ScriptItem]
    analytical_filter: AnalyticalFilter


class VideoAnalysisResult(BaseModel):
    analysis: MasterBreakdown
    reproduction_prompt: str = Field(
        description="Professional director-level prompt for recreating a similar video."
    )


SYSTEM_INSTRUCTION = """
Ты — профессиональный режиссёр, оператор, монтажный режиссёр и креативный стратег.
Проведи полный режиссёрский разбор загруженного видео по методике Master Breakdown Ultimate Edition.

ОБЯЗАТЕЛЬНО ЗАПОЛНИ ВСЕ 7 ШАГОВ:
Шаг 0. Концепция и месседж (Core Idea / DNA): логлайн, метафора, целевое действие, стратегическая задача.
Шаг 1. Сюжет и драматургия: жанр, герой и арка, экспозиция, инцидент/кульминация, развязка, экранный текст/POV.
Шаг 2. Звуковая партитура: музыка и предполагаемый BPM/настроение, SFX/Foley, The Drop, звуковые мосты.
Шаг 3. Хореография и геометрия: передний/средний/задний планы, движение по X/Y/Z, точные глаголы действия.
Шаг 4. Технический стек: состояние и движение камеры, ракурс, оптика, глубина резкости, FPS/скорость.
Шаг 5. Арт-дирекшн и цвет: палитра, визуальные рифмы, свет, ключевой реквизит.
Шаг 6. Психология монтажа: темп, хук первых 3 секунд, интрига, финальное вознаграждение, диегезис, match-cut, эмоциональная кривая.

ОБЯЗАТЕЛЬНЫЕ ДОПОЛНЕНИЯ:
- Script Breakdown: подробная таблица по таймкодам со сценой/действием, текстом/звуком и смысловой нагрузкой.
- Analytical Filter: принцип одной цели, эмпатия через усилие, логика метафоры, честность CGI, точка drop-off, единство фокуса.
- Reproduction Prompt: подробный профессиональный промпт для создания похожего видео, основанный именно на фактическом анализе загруженного ролика.

Не используй N/A. Если режиссёрский параметр нельзя измерить абсолютно точно, дай профессиональную оценку и явно формулируй её как оценку.
Ответ дай на русском языке. Reproduction Prompt можно писать на английском, если так он полезнее для видеогенератора.
"""


def _client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return genai.Client(api_key=api_key)


def analyze_video(video_path: str) -> dict:
    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    client = _client()
    uploaded = client.files.upload(file=str(path))

    while not uploaded.state or uploaded.state.name == "PROCESSING":
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)

    if uploaded.state.name != "ACTIVE":
        raise RuntimeError(f"Gemini video processing failed: {uploaded.state.name}")

    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    response = client.models.generate_content(
        model=model,
        contents=[
            uploaded,
            "Проанализируй это видео строго по системной инструкции и верни полный структурированный режиссёрский разбор.",
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=VideoAnalysisResult,
        ),
    )
    if not response.text:
        raise RuntimeError("Gemini returned an empty analysis")

    result = VideoAnalysisResult.model_validate_json(response.text)
    return json.loads(result.model_dump_json())
