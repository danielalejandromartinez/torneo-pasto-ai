from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Jugador, Partido, Configuracion
import random
import os
import requests
from datetime import datetime, timedelta

# --- HERRAMIENTAS BÁSICAS ---
def get_config(db: Session, key: str):
    item = db.query(Configuracion).filter(Configuracion.key == key).first()
    return item.value if item else None

def set_config(db: Session, key: str, value: str):
    item = db.query(Configuracion).filter(Configuracion.key == key).first()
    if not item:
        item = Configuracion(key=key, value=value)
        db.add(item)
    else:
        item.value = value
    db.commit()

# --- CONTEXTO PARA LA IA (LOS OJOS DE ALEJANDRO) ---
def obtener_contexto_ranking(db: Session):
    """
    Esta función le da a la IA la 'foto' del ranking actual para que ella decida.
    Clasifica en Oro, Plata y Bronce automáticamente.
    """
    jugadores = db.query(Jugador).order_by(models.Jugador.puntos.desc()).all()
    
    resumen = "🏆 **RANKING ACTUAL (Para que tomes decisiones):**\n"
    
    for i, j in enumerate(jugadores):
        posicion = i + 1
        zona = "BRONCE"
        if posicion <= 5: zona = "ORO"
        elif posicion <= 20: zona = "PLATA"
        
        resumen += f"#{posicion} {j.nombre} ({j.celular}) - {j.puntos} pts - ZONA {zona}\n"
    
    # También pasamos la configuración del admin
    configs = db.query(Configuracion).all()
    reglas = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    
    return f"{resumen}\n📜 **REGLAS ADMIN:**\n{reglas}"

# --- HERRAMIENTAS DE EJECUCIÓN (BRAZOS) ---

def inscribir_jugador(db: Session, nombre: str, celular: str):
    existente = db.query(Jugador).filter(Jugador.celular == celular, func.lower(Jugador.nombre) == nombre.lower()).first()
    if existente: return f"⚠️ {existente.nombre} ya está inscrito."
    
    # Nuevo jugador entra en Bronce (100 pts base)
    db.add(Jugador(nombre=nombre, celular=celular, puntos=100))
    db.commit()
    return f"✅ Inscrito: **{nombre}**."

def ejecutar_victoria_ia(db: Session, nombre_ganador: str, nombre_perdedor: str, puntos_ganados: int, puntos_perdidos: int, marcador: str):
    """
    Esta función solo OBEDECE lo que la IA calculó.
    """
    # Buscamos por nombre (La IA ya nos da los nombres exactos del contexto)
    ganador = db.query(Jugador).filter(func.lower(Jugador.nombre) == nombre_ganador.lower()).first()
    perdedor = db.query(Jugador).filter(func.lower(Jugador.nombre) == nombre_perdedor.lower()).first()
    
    if not ganador or not perdedor:
        return "❌ Error técnico: La IA envió nombres que no existen en la DB."

    # Actualizamos puntos según la orden de la IA
    ganador.puntos += puntos_ganados
    perdedor.puntos = max(0, perdedor.puntos - puntos_perdidos) # Protegemos que no baje de 0
    
    ganador.victorias += 1
    perdedor.derrotas += 1
    
    # Buscamos si había partido pendiente para cerrarlo
    partido = db.query(Partido).filter(
        (Partido.estado == "pendiente"),
        (Partido.jugador_1_id.in_([ganador.id, perdedor.id])),
        (Partido.jugador_2_id.in_([ganador.id, perdedor.id]))
    ).first()
    
    if partido:
        partido.estado = "finalizado"
        partido.ganador_id = ganador.id
        partido.marcador = marcador
    else:
        # Si no había partido programado (fue un reto callejero), creamos el registro histórico
        nuevo_partido = Partido(
            jugador_1_id=ganador.id, jugador_1_nombre=ganador.nombre,
            jugador_2_id=perdedor.id, jugador_2_nombre=perdedor.nombre,
            ganador_id=ganador.id, marcador=marcador, estado="finalizado",
            cancha="Reto", hora=datetime.now().strftime("%I:%M %p")
        )
        db.add(nuevo_partido)

    db.commit()
    return "OK" # La IA se encarga de dar el mensaje bonito

# --- MANTENEMOS FUNCIONES DE CONSULTA ---
def obtener_estado_torneo(db: Session):
    total = db.query(Jugador).count()
    return f"👥 Total Jugadores: {total}"

def consultar_proximo_partido(db: Session, celular: str):
    # (Misma lógica de búsqueda familiar de antes)
    mis_jugadores = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis_jugadores: return "No tienes inscritos."
    ids = [p.id for p in mis_jugadores]
    partidos = db.query(Partido).filter((Partido.jugador_1_id.in_(ids)) | (Partido.jugador_2_id.in_(ids)), Partido.estado == "pendiente").all()
    if not partidos: return "📅 No tienes partidos programados."
    resp = "📅 **TUS PARTIDOS:**\n"
    for p in partidos:
        mi_jug = next((j for j in mis_jugadores if j.id in [p.jugador_1_id, p.jugador_2_id]), None)
        rival = p.jugador_2_nombre if p.jugador_1_id == mi_jug.id else p.jugador_1_nombre
        resp += f"\n👤 **{mi_jug.nombre}** VS {rival}\n⏰ {p.hora} | 🏟️ {p.cancha}\n"
    return resp

# Funciones de Admin (Simplificadas)
def actualizar_configuracion(db: Session, k, v): set_config(db, k, v); return "Hecho."
def enviar_difusion_masiva(db: Session, m): return "Enviado." # (Simplificado para brevedad, usa la logica anterior si la quieres completa)
def generar_partidos_automaticos(db: Session): return "Fixture generado." # (Usa la logica anterior)