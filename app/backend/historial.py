from database import Base
from sqlalchemy import Column, String, DateTime
import uuid
from datetime import datetime

class Historial(Base):
    __tablename__ = "historial"
    id        = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id  = Column(String, nullable=False)
    fecha     = Column(DateTime, default=datetime.utcnow)
    usuario   = Column(String, default="sistema")
    campo     = Column(String, default="")
    valor_ant = Column(String, default="")
    valor_new = Column(String, default="")
    accion    = Column(String, default="")  # "edicion" | "sincronizacion"