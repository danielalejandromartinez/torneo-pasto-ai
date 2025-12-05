from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean
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
    categoria = Column(String, default="Novatos") # Oro, Plata, Bronce (Calculado en logica)
    partidos_jugados = Column(Integer, default=0)
    victorias = Column(Integer, default=0)
    derrotas = Column(Integer, default=0)

class Partido(Base):
    __tablename__ = "partidos"
    id = Column(Integer, primary_key=True, index=True)
    
    # Jugadores
    jugador_1_id = Column(Integer, ForeignKey("jugadores.id"))
    jugador_1_nombre = Column(String)
    jugador_2_id = Column(Integer, ForeignKey("jugadores.id"))
    jugador_2_nombre = Column(String)
    
    # Estado: 'pendiente', 'esperando_confirmacion', 'finalizado'
    estado = Column(String, default="pendiente")
    
    # Datos finales
    ganador_id = Column(Integer, nullable=True)
    marcador = Column(String, nullable=True)
    
    # DATOS DEL VAR (Temporal mientras confirman)
    temp_reportado_por = Column(String, nullable=True) # Celular de quien reportó
    temp_ganador_id = Column(Integer, nullable=True)
    
    # Logística
    cancha = Column(String, default="Por definir")
    hora = Column(String, default="Por definir")

class Noticia(Base):
    __tablename__ = "noticias"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String)
    cuerpo = Column(Text)
    tipo = Column(String)
    fecha = Column(DateTime, default=datetime.now)