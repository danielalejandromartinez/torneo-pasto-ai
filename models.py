from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from database import Base
from datetime import datetime

class Configuracion(Base):
    __tablename__ = "configuracion"
    key = Column(String, primary_key=True, index=True)
    value = Column(String)

class Jugador(Base):
    __tablename__ = "jugadores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    
    # CAMBIO IMPORTANTE: Ya NO dice unique=True.
    # Ahora muchos jugadores pueden tener el mismo celular (Familia).
    celular = Column(String, index=True) 
    
    puntos = Column(Integer, default=100) 
    categoria = Column(String, default="Novatos")
    
    # Estadísticas
    partidos_jugados = Column(Integer, default=0)
    victorias = Column(Integer, default=0)
    derrotas = Column(Integer, default=0)

class Partido(Base):
    __tablename__ = "partidos"

    id = Column(Integer, primary_key=True, index=True)
    
    jugador_1_id = Column(Integer, ForeignKey("jugadores.id"))
    jugador_1_nombre = Column(String)
    jugador_2_id = Column(Integer, ForeignKey("jugadores.id"))
    jugador_2_nombre = Column(String)
    
    estado = Column(String, default="pendiente")
    ganador_id = Column(Integer, nullable=True)
    marcador = Column(String, nullable=True)
    
    cancha = Column(String, default="Por definir")
    hora = Column(String, default="Por definir")