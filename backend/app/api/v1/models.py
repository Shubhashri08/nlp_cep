from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.database.session import get_db
from backend.app.models.entities import ModelRegistry

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("")
def get_registered_models(include_archived: bool = False, db: Session = Depends(get_db)):
    q = db.query(ModelRegistry)
    if not include_archived:
        q = q.filter(ModelRegistry.status == "ACTIVE")
    return [{"id": m.id, "model_name": m.model_name, "model_type": m.model_type, "version": m.version,
             "training_dataset": m.training_dataset, "training_date": m.training_date.strftime("%Y-%m-%d %H:%M"),
             "parameters": m.parameters, "metrics": m.metrics, "status": m.status}
            for m in q.order_by(ModelRegistry.model_type, ModelRegistry.model_name).all()]
