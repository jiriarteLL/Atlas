from database import Base
from sqlalchemy import Column, String, DateTime, Integer
import uuid
from datetime import datetime

class Adjunto(Base):
    __tablename__ = "adjuntos"
    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id    = Column(String, nullable=False)
    nombre      = Column(String, default="")
    archivo     = Column(String, default="")
    tipo        = Column(String, default="")
    tamano      = Column(Integer, default=0)
    descripcion = Column(String, default="")
    subido_por  = Column(String, default="")
    fecha       = Column(DateTime, default=datetime.utcnow)
    activo      = Column(String, default="1")
