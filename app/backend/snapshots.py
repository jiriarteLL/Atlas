from database import Base
from sqlalchemy import Column, String, DateTime, Integer
import uuid
from datetime import datetime

class Snapshot(Base):
    __tablename__ = "snapshots"
    id       = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    fecha    = Column(DateTime, default=datetime.utcnow)
    metrica  = Column(String, default="")
    clave    = Column(String, default="")
    valor    = Column(Integer, default=0)
