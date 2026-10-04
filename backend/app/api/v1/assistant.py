from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import audit, get_current_user
from backend.app.database.session import get_db
from backend.app.llm.assistant import planning_assistant
from backend.app.llm.providers import get_llm
from backend.app.models.entities import User
from backend.app.schemas.dss_schemas import AssistantQueryRequest, AssistantQueryResponse

router = APIRouter()


@router.get("/status")
def assistant_status(_: User = Depends(get_current_user)):
    llm = get_llm()
    return {"provider": llm.name, "model": llm.model or None, "llm_available": llm.available,
            "budget": llm.budget.usage() if hasattr(llm, "budget") else None,
            "models": getattr(llm, "models", None),
            "mode": "LLM tool-calling over municipal database" if llm.available else "Rule-based intents over municipal database"}


@router.post("/query", response_model=AssistantQueryResponse)
def query_ai_assistant(payload: AssistantQueryRequest, request: Request, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    """Grounded planning assistant: answers are generated only from database / GIS query results, with citations."""
    res = planning_assistant.answer_query(payload.question, db, payload.context_ward_id)
    audit(db, user, "ASSISTANT_QUERY", "ASSISTANT", None, {"intent": res["intent"], "provider": res["provider"]}, request)
    db.commit()
    return AssistantQueryResponse(**res)
