from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.schemas.dss_schemas import AssistantQueryRequest, AssistantQueryResponse
from backend.app.llm.assistant import planning_assistant

router = APIRouter()

@router.post("/query", response_model=AssistantQueryResponse)
def query_ai_assistant(
    payload: AssistantQueryRequest,
    db: Session = Depends(get_db)
):
    """
    Controlled Grounded Planning Assistant endpoint:
    Parses natural language query, detects intent, queries municipal database/GIS layers,
    and returns factual synthesis with traceable evidence sources.
    """
    res = planning_assistant.answer_query(
        question=payload.question,
        db=db,
        context_ward_id=payload.context_ward_id
    )
    return AssistantQueryResponse(**res)
