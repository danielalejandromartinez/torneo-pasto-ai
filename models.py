from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from database import Base
from datetime import datetime

class Configuracion(Base):
    __tablename__ = "configuracion"
    # Esta tabla es la "Libreta" de Alejandro
    key = Column(String, primary_key=True, index=True) # Ej: "fecha_inicio", "precio"
    value = Column(String) # Ej: "15 de Noviembre", "50.000"

class Jugador(Base):
    __tablename__ = "jugadores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    celular = Column(String, unique=True, index=True)
    puntos = Column(Integer, default=100) 
    categoria = Column(String, default="Novatos")
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