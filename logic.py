from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Jugador, Partido, Configuracion
import random
import os
import requests
from datetime import datetime

# --- HERRAMIENTAS DE MEMORIA ---
def obtener_contexto_completo(db: Session):
    """
    Le entrega a la IA todo lo que necesita saber para trabajar:
    1. Lista exacta de jugadores.
    2. Partidos que ya existen (por si hay que reprogramar).
    """
    jugadores = db.query(Jugador).all()
    lista_jugadores = []
    for j in jugadores:
        lista_jugadores.append(f"- ID: {j.id} | Nombre: {j.nombre} | Celular: {j.celular} | Puntos: {j.puntos}")
    
    texto_jugadores = "\n".join(lista_jugadores) if lista_jugadores else "No hay inscritos."
    
    partidos = db.query(Partido).filter(Partido.estado == "pendiente").all()
    lista_partidos = "\n".join([f"- {p.jugador_1_nombre} vs {p.jugador_2_nombre} ({p.hora})" for p in partidos])
    
    return f"""
    === BASE DE DATOS ACTUAL ===
    JUGADORES INSCRITOS:
    {texto_jugadores}
    
    PARTIDOS PENDIENTES:
    {lista_partidos}
    ============================
    """

# --- HERRAMIENTAS DE EJECUCIÓN (BRAZOS) ---

def inscribir_jugador(db: Session, nombre: str, celular: str):
    # Verificación simple para no duplicar nombres exactos en el mismo cel
    existente = db.query(Jugador).filter(Jugador.celular == celular, func.lower(Jugador.nombre) == nombre.lower()).first()
    if existente: return f"⚠️ {existente.nombre} ya está inscrito."
    
    db.add(Jugador(nombre=nombre, celular=celular, puntos=100))
    db.commit()
    total = db.query(Jugador).filter(Jugador.celular == celular).count()
    return f"✅ Inscrito: **{nombre}**."

def guardar_organizacion_ia(db: Session, lista_partidos: list):
    """
    La IA es la jefa. Ella nos manda la lista de partidos, nosotros solo guardamos.
    Formato esperado: [{'j1_nombre': 'X', 'j2_nombre': 'Y', 'hora': '...', 'cancha': '...'}]
    """
    # 1. Limpiamos la programación anterior (re-organización)
    db.query(Partido).filter(Partido.estado == "pendiente").delete()
    
    creados = 0
    for p in lista_partidos:
        # Buscamos a los jugadores por nombre (La IA debe ser precisa)
        j1 = db.query(Jugador).filter(func.lower(Jugador.nombre) == p['j1_nombre'].lower()).first()
        j2 = db.query(Jugador).filter(func.lower(Jugador.nombre) == p['j2_nombre'].lower()).first()
        
        if j1 and j2:
            nuevo = Partido(
                jugador_1_id=j1.id, jugador_1_nombre=j1.nombre,
                jugador_2_id=j2.id, jugador_2_nombre=j2.nombre,
                cancha=str(p.get('cancha', '1')),
                hora=str(p.get('hora', 'Por definir')),
                estado="pendiente"
            )
            db.add(nuevo)
            creados += 1
            
    db.commit()
    return f"✅ **¡Organización Completada!**\nHe creado {creados} partidos siguiendo tus instrucciones.\nRevisa la web: https://torneo-pasto-ai.onrender.com"

def registrar_victoria(db: Session, celular: str, nombre_ganador_detectado: str, nombre_perfil_wa: str, s1: int, s2: int):
    # Lógica de encontrar el partido
    mis_jugadores = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis_jugadores: return "No tienes perfiles inscritos."
    ids = [p.id for p in mis_jugadores]
    
    partidos = db.query(Partido).filter((Partido.jugador_1_id.in_(ids)) | (Partido.jugador_2_id.in_(ids)), Partido.estado == "pendiente").all()
    if not partidos: return "No tienes partidos pendientes."
    
    partido_objetivo = None
    mi_jugador_ganador = None
    candidato = nombre_ganador_detectado if nombre_ganador_detectado else nombre_perfil_wa
    
    if len(partidos) == 1:
        partido_objetivo = partidos[0]
        mi_jugador_ganador = db.query(Jugador).get(partido_objetivo.jugador_1_id if partido_objetivo.jugador_1_id in ids_jugadores else partido_objetivo.jugador_2_id)
    else:
        # Busqueda inteligente
        for p in partidos:
            j1 = db.query(Jugador).get(p.jugador_1_id)
            j2 = db.query(Jugador).get(p.jugador_2_id)
            if candidato and candidato.lower() in j1.nombre.lower() and j1.id in ids_jugadores:
                partido_objetivo = p; mi_jugador_ganador = j1; break
            elif candidato and candidato.lower() in j2.nombre.lower() and j2.id in ids_jugadores:
                partido_objetivo = p; mi_jugador_ganador = j2; break
        
        if not partido_objetivo: return f"❌ No encontré partido para **{candidato}**."

    # Lógica de Puntos (Bounty simple +10/-10 para empezar)
    id_perdedor = partido_objetivo.jugador_2_id if partido_objetivo.jugador_1_id == mi_jugador_ganador.id else partido_objetivo.jugador_1_id
    perdedor = db.query(Jugador).get(id_perdedor)
    
    mi_jugador_ganador.puntos += 10
    perdedor.puntos = max(0, perdedor.puntos - 10)
    mi_jugador_ganador.victorias += 1
    perdedor.derrotas += 1
    partido_objetivo.estado = "finalizado"
    partido_objetivo.ganador_id = mi_jugador_ganador.id
    partido_objetivo.marcador = f"{s1}-{s2}"
    
    db.commit()
    return f"🏆 **¡VICTORIA!**\nGanador: {mi_jugador_ganador.nombre}\nRanking actualizado."

# --- CONSULTAS SIMPLES ---
def obtener_estado_torneo(db: Session):
    total = db.query(Jugador).count()
    pendientes = db.query(Partido).filter(Partido.estado == "pendiente").count()
    return f"📊 *Estado*\n👥 Inscritos: {total}\n🎾 Partidos Pendientes: {pendientes}"

def consultar_proximo_partido(db: Session, celular: str):
    mis_jugadores = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis_jugadores: return "No tienes inscritos."
    ids = [p.id for p in mis_jugadores]
    partidos = db.query(Partido).filter((Partido.jugador_1_id.in_(ids)) | (Partido.jugador_2_id.in_(ids)), Partido.estado == "pendiente").all()
    if not partidos: return "📅 No tienes partidos."
    resp = "📅 **TUS PARTIDOS:**\n"
    for p in partidos:
        mi_jug = next((j for j in mis_jugadores if j.id in [p.jugador_1_id, p.jugador_2_id]), None)
        rival = p.jugador_2_nombre if p.jugador_1_id == mi_jug.id else p.jugador_1_nombre
        resp += f"\n👤 **{mi_jug.nombre}** VS {rival}\n⏰ {p.hora} | 🏟️ {p.cancha}\n"
    return resp