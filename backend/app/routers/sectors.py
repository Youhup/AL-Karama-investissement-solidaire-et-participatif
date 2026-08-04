from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sector import Sector
from app.schemas.sector import SectorOut

router = APIRouter(prefix="/sectors", tags=["Sectors"])


@router.get("", response_model=list[SectorOut])
def list_sectors(db: Session = Depends(get_db)):
    return db.query(Sector).order_by(Sector.name).all()
