from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Jugador(Base):
    __tablename__ = "jugadores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    telefono = Column(String, unique=True, index=True) # El ID de WhatsApp
    ranking_inicial = Column(Integer, default=0) # Ranking con el que entra al torneo
    
    # Estadísticas para la Fase de Grupos
    grupo = Column(String, nullable=True) # Ejemplo: "A", "B", "C"
    puntos = Column(Integer, default=0) # 3 ganar, 1 perder
    partidos_jugados = Column(Integer, default=0)
    sets_ganados = Column(Integer, default=0)
    sets_perdidos = Column(Integer, default=0)

class Partido(Base):
    __tablename__ = "partidos"

    id = Column(Integer, primary_key=True, index=True)
    
    # Quiénes juegan (Relaciones)
    jugador_1_id = Column(Integer, ForeignKey("jugadores.id"))
    jugador_2_id = Column(Integer, ForeignKey("jugadores.id"))
    
    jugador_1 = relationship("Jugador", foreign_keys=[jugador_1_id])
    jugador_2 = relationship("Jugador", foreign_keys=[jugador_2_id])
    
    # Detalles del partido
    fase = Column(String) # "Grupo", "Octavos", "Cuartos", "Final"
    grupo = Column(String, nullable=True) # Solo si es fase de grupos
    
    marcador_sets = Column(String, default="0-0") # Ejemplo "3-1"
    ganador_id = Column(Integer, ForeignKey("jugadores.id"), nullable=True)
    
    estado = Column(String, default="pendiente") # "pendiente", "finalizado"
    cancha = Column(String, nullable=True) # "Cancha 1"