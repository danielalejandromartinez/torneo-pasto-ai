from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
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
    celular = Column(String, index=True)
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

# --- NUEVA TABLA: EL NOTICIERO ---
class Noticia(Base):
    __tablename__ = "noticias"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String) # Ej: "¡BATACAZO EN LA CANCHA 1!"
    cuerpo = Column(Text)   # Ej: "Daniel Martínez vence a..."
    tipo = Column(String)   # 'partido', 'anuncio', 'ranking'
    fecha = Column(DateTime, default=datetime.now)