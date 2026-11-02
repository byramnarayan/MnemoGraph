from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.schemas.answer import AnswerRequest, AnswerResponse, ContextAnswerRequest
from app.services.answer_service import AnswerService

router = APIRouter()
answer_service = AnswerService()


@router.post("", response_model=AnswerResponse)
async def get_answer(
    req: AnswerRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await answer_service.generate_answer(
            db=db,
            req=req,
            current_user_email=current_user.email,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Answer generation error: {str(e)}")


@router.post("/context", response_model=AnswerResponse)
async def get_context_answer(
    req: ContextAnswerRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await answer_service.generate_context_answer(
            db=db,
            req=req,
            current_user_email=current_user.email,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context answer generation error: {str(e)}")

