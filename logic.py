from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Jugador, Partido, Configuracion
import random
import os
import requests
from datetime import datetime, timedelta

# ==========================================
# 🛠️ HERRAMIENTAS DE MEMORIA (CONFIGURACIÓN)
# ==========================================

def get_config_value(db: Session, key: str):
    item = db.query(Configuracion).filter(Configuracion.key == key).first()
    return item.value if item else None

def set_config_value(db: Session, key: str, value: str):
    item = db.query(Configuracion).filter(Configuracion.key == key).first()
    if not item:
        item = Configuracion(key=key, value=value)
        db.add(item)
    else:
        item.value = value
    db.commit()

# --- CONTEXTO TOTAL (LO QUE ALEJANDRO SABE) ---
def obtener_contexto_completo(db: Session):
    """
    Recopila TODO: Jugadores inscritos y reglas configuradas.
    La IA usará esto para decidir qué falta.
    """
    # 1. Jugadores
    jugadores = db.query(Jugador).all()
    lista_jugadores = "\n".join([f"- {j.nombre} ({j.celular})" for j in jugadores])
    if not lista_jugadores: lista_jugadores = "Ninguno"
    
    # 2. Configuración guardada
    configs = db.query(Configuracion).all()
    lista_config = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    if not lista_config: lista_config = "Ninguna regla definida aún."
    
    return f"""
    --- ESTADO ACTUAL DE LA BASE DE DATOS ---
    JUGADORES INSCRITOS ({len(jugadores)}):
    {lista_jugadores}
    
    CONFIGURACIÓN ACTUAL (MEMORIA):
    {lista_config}
    -----------------------------------------
    """

# ==========================================
# 🧠 BRAZOS EJECUTORES (OBEDECEN A LA IA)
# ==========================================

def guardar_configuracion_ia(db: Session, clave: str, valor: str):
    """La IA decidió que aprendió un dato nuevo (ej: num_canchas)"""
    set_config_value(db, clave, valor)
    return f"📝 Entendido. Guardé en mi memoria: **{clave}** = **{valor}**."

def guardar_fixture_ia(db: Session, lista_partidos: list):
    """
    La IA generó el cuadro completo. Aquí solo lo guardamos en la DB.
    Recibe una lista de diccionarios: [{'j1': 'Daniel', 'j2': 'Juan', 'hora': '3:00 PM', 'cancha': '1'}]
    """
    # 1. Limpiar partidos pendientes viejos
    db.query(Partido).filter(Partido.estado == "pendiente").delete()
    
    creados = 0
    errores = []
    
    for p in lista_partidos:
        # Buscar IDs
        j1 = db.query(Jugador).filter(func.lower(Jugador.nombre) == p['j1'].lower()).first()
        j2 = db.query(Jugador).filter(func.lower(Jugador.nombre) == p['j2'].lower()).first()
        
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
        else:
            errores.append(f"{p['j1']} vs {p['j2']}")
            
    db.commit()
    return f"✅ **¡PROGRAMACIÓN LISTA!**\nHe creado {creados} partidos automáticamente basándome en los inscritos y horarios definidos.\n\nRevisa la web: https://torneo-pasto-ai.onrender.com"

# --- HERRAMIENTAS CLÁSICAS (INSCRIPCIÓN Y VICTORIA) ---

def inscribir_jugador(db: Session, nombre: str, celular: str):
    existente = db.query(Jugador).filter(Jugador.celular == celular, func.lower(Jugador.nombre) == nombre.lower()).first()
    if existente: return f"⚠️ {existente.nombre} ya está inscrito."
    db.add(Jugador(nombre=nombre, celular=celular, puntos=100))
    db.commit()
    total = db.query(Jugador).filter(Jugador.celular == celular).count()
    return f"✅ Inscrito: **{nombre}**. (Perfil #{total} en este cel)."

def consultar_proximo_partido(db: Session, celular: str):
    mis_jugadores = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis_jugadores: return "No tienes perfiles inscritos."
    ids = [p.id for p in mis_jugadores]
    partidos = db.query(Partido).filter((Partido.jugador_1_id.in_(ids)) | (Partido.jugador_2_id.in_(ids)), Partido.estado == "pendiente").all()
    if not partidos: return "📅 No tienes partidos programados."
    resp = "📅 **TUS PARTIDOS:**\n"
    for p in partidos:
        mi_jug = next((j for j in mis_jugadores if j.id in [p.jugador_1_id, p.jugador_2_id]), None)
        rival = p.jugador_2_nombre if p.jugador_1_id == mi_jug.id else p.jugador_1_nombre
        resp += f"\n👤 **{mi_jug.nombre}** VS {rival}\n⏰ {p.hora} | 🏟️ {p.cancha}\n"
    return resp

def registrar_victoria(db: Session, celular: str, nombre_ganador_detectado: str, nombre_perfil_wa: str, s1: int, s2: int):
    mis_jugadores = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis_jugadores: return "No tienes perfiles."
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
        for p in partidos:
            j1 = db.query(Jugador).get(p.jugador_1_id)
            j2 = db.query(Jugador).get(p.jugador_2_id)
            if candidato and candidato.lower() in j1.nombre.lower() and j1.id in ids_jugadores:
                partido_objetivo = p; mi_jugador_ganador = j1; break
            elif candidato and candidato.lower() in j2.nombre.lower() and j2.id in ids_jugadores:
                partido_objetivo = p; mi_jugador_ganador = j2; break
        if not partido_objetivo: return f"❌ No encontré partido para **{candidato}**."

    id_perdedor = partido_objetivo.jugador_2_id if partido_objetivo.jugador_1_id == mi_jugador_ganador.id else partido_objetivo.jugador_1_id
    perdedor = db.query(Jugador).get(id_perdedor)
    
    # REGLAS BOUNTY
    if perdedor.puntos > mi_jugador_ganador.puntos: pts = 20 # Batacazo
    else: pts = 10 # Normal
    
    mi_jugador_ganador.puntos += pts
    perdedor.puntos = max(0, perdedor.puntos - pts)
    mi_jugador_ganador.victorias += 1
    perdedor.derrotas += 1
    partido_objetivo.estado = "finalizado"
    partido_objetivo.ganador_id = mi_jugador_ganador.id
    partido_objetivo.marcador = f"{s1}-{s2}"
    db.commit()
    return f"🏆 **¡VICTORIA!**\nGanador: {mi_jugador_ganador.nombre} (+{pts})\nRanking actualizado."

# Mantener para compatibilidad
def obtener_estado_torneo(db: Session): return obtener_contexto_completo(db)
def enviar_difusion_masiva(db: Session, m): return "Enviado."