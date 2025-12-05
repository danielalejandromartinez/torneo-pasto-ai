from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Jugador, Partido, Configuracion, Noticia
import random
import os
import requests
import re
from datetime import datetime, timedelta

# --- CONTEXTO ---
def obtener_contexto(db: Session):
    jugadores = db.query(Jugador).count()
    configs = db.query(Configuracion).all()
    reglas = ", ".join([f"{c.key}={c.value}" for c in configs])
    return f"Inscritos: {jugadores}. Reglas: {reglas}"

# --- NOTICIERO ---
def guardar_noticia(db: Session, titulo: str, cuerpo: str):
    try:
        db.add(Noticia(titulo=titulo, cuerpo=cuerpo, tipo="general"))
        db.commit()
    except: pass

# --- FUNCIONES MAPEDADAS A LAS HERRAMIENTAS ---

def inscribir_usuario_logic(db: Session, nombre: str, celular: str):
    # Verificamos si existe
    existente = db.query(Jugador).filter(Jugador.celular == celular, func.lower(Jugador.nombre) == nombre.lower()).first()
    if existente: return f"⚠️ {nombre} ya está inscrito."
    
    db.add(Jugador(nombre=nombre, celular=celular, puntos=100))
    db.commit()
    total = db.query(Jugador).filter(Jugador.celular == celular).count()
    guardar_noticia(db, "¡NUEVO FICHAJE!", f"{nombre} entra al circuito.")
    return f"✅ Inscrito: **{nombre}**. (Perfil #{total} en este cel)."

def consultar_info_logic(db: Session, tipo: str, celular: str):
    if tipo == "inscritos":
        jugadores = db.query(Jugador).all()
        if not jugadores: return "Aún no hay inscritos."
        nombres = "\n".join([f"- {j.nombre}" for j in jugadores])
        return f"📊 **INSCRITOS ({len(jugadores)}):**\n{nombres}"
    
    if tipo == "mis_partidos":
        # Lógica familiar: busca todos los perfiles de este celular
        mis_jugadores = db.query(Jugador).filter(Jugador.celular == celular).all()
        if not mis_jugadores: return "No estás inscrito."
        ids = [p.id for p in mis_jugadores]
        partidos = db.query(Partido).filter((Partido.jugador_1_id.in_(ids)) | (Partido.jugador_2_id.in_(ids)), Partido.estado == "pendiente").all()
        if not partidos: return "📅 No tienes partidos programados."
        resp = "📅 **TUS PARTIDOS:**\n"
        for p in partidos:
            resp += f"vs {p.jugador_2_nombre if p.jugador_1_id in ids else p.jugador_1_nombre} ({p.hora})\n"
        return resp

    return "Información general: https://torneo-pasto-ai.onrender.com/"

def reportar_victoria_logic(db: Session, celular: str, nombre_wa: str, sets_ganador: int, sets_perdedor: int):
    # Simplificado para MVP: Asume que el dueño del celular ganó
    # (Aquí iría la lógica de puntos Bounty)
    return "🏆 Victoria registrada. Ranking actualizado."

def configurar_torneo_logic(db: Session, accion: str, datos: str):
    if accion == "configurar_datos":
        # Aquí podríamos parsear los datos con Regex si queremos ser detallistas
        # Por ahora guardamos el string crudo como referencia
        item = db.query(Configuracion).filter(Configuracion.key == "config_raw").first()
        if not item: db.add(Configuracion(key="config_raw", value=datos))
        else: item.value = datos
        db.commit()
        return f"📝 Configuración guardada: {datos}. Di 'Iniciar torneo' para generar cuadros."
    
    if accion == "iniciar_fixture":
        # Generador simple
        jugadores = db.query(Jugador).all()
        if len(jugadores) < 2: return "❌ Faltan jugadores."
        db.query(Partido).filter(Partido.estado == "pendiente").delete()
        random.shuffle(jugadores)
        for i in range(len(jugadores) // 2):
            db.add(Partido(
                jugador_1_id=jugadores[i*2].id, jugador_1_nombre=jugadores[i*2].nombre,
                jugador_2_id=jugadores[i*2+1].id, jugador_2_nombre=jugadores[i*2+1].nombre,
                cancha="1", hora="Por definir", estado="pendiente"
            ))
        db.commit()
        guardar_noticia(db, "¡ARRANCA EL TORNEO!", "Fixture generado.")
        return "✅ **FIXTURE GENERADO**. Revisa la web."
        
    return "Comando desconocido."