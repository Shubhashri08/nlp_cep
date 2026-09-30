from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import ModelRegistry

router = APIRouter()

@router.get("")
def get_registered_models(db: Session = Depends(get_db)):
    models = db.query(ModelRegistry).order_by(ModelRegistry.training_date.desc()).all()
    return [{
        "id": m.id,
        "model_name": m.model_name,
        "model_type": m.model_type,
        "version": m.version,
        "training_dataset": m.training_dataset,
        "training_date": m.training_date.strftime("%Y-%m-%d"),
        "parameters": m.parameters,
        "metrics": m.metrics,
        "status": m.status
    } for m in models]
