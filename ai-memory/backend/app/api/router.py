from fastapi import APIRouter

from app.api.accounts import router as accounts_router
from app.api.pipeline import router as pipeline_router
from app.api.decision import router as decision_router
from app.api.knowledge import router as knowledge_router
from app.api.learning import router as learning_router
from app.api.prediction import router as prediction_router
from app.api.prompts import router as prompts_router
from app.api.trends import router as trends_router
from app.api.videos import router as videos_router
from app.api.workflow import router as workflow_router

api_router = APIRouter()
api_router.include_router(accounts_router)
api_router.include_router(pipeline_router)
api_router.include_router(learning_router)
api_router.include_router(prediction_router)
api_router.include_router(knowledge_router)
api_router.include_router(trends_router)
api_router.include_router(decision_router)
api_router.include_router(prompts_router)
api_router.include_router(videos_router)
api_router.include_router(workflow_router)
