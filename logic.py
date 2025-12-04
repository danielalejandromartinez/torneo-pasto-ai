from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Jugador, Partido, Configuracion, Noticia
import random
import os
import requests
from datetime import datetime, timedelta

# --- HERRAMIENTAS BASE ---
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

def obtener_contexto_completo(db: Session):
    jugadores = db.query(Jugador).order_by(Jugador.puntos.desc()).all()
    lista_jugadores = "\n".join([f"- {j.nombre} ({j.puntos} pts)" for j in jugadores])
    if not lista_jugadores: lista_jugadores = "Ninguno"
    
    configs = db.query(Configuracion).all()
    lista_config = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    
    return f"--- RANKING ACTUAL ---\n{lista_jugadores}\n--- REGLAS ---\n{lista_config}"

# --- NOTICIAS ---
def guardar_noticia(db: Session, titulo: str, cuerpo: str, tipo: str="general"):
    """Publica una noticia en el muro"""
    nueva = Noticia(titulo=titulo, cuerpo=cuerpo, tipo=tipo)
    db.add(nueva)
    db.commit()

# --- ACCIONES ---
def inscribir_jugador(db: Session, nombre: str, celular: str):
    existente = db.query(Jugador).filter(Jugador.celular == celular, func.lower(Jugador.nombre) == nombre.lower()).first()
    if existente: return f"⚠️ {existente.nombre} ya está inscrito."
    
    db.add(Jugador(nombre=nombre, celular=celular, puntos=100))
    db.commit()
    
    # Generamos noticia automática de bienvenida
    guardar_noticia(db, "¡NUEVO RETADOR!", f"{nombre} se une al circuito con 100 puntos. ¡Tiemblan los favoritos!", "anuncio")
    
    return f"✅ Inscrito: **{nombre}**."

def guardar_fixture_ia(db: Session, lista_partidos: list):
    db.query(Partido).filter(Partido.estado == "pendiente").delete()
    creados = 0
    for p in lista_partidos:
        j1 = db.query(Jugador).filter(func.lower(Jugador.nombre) == p['j1_nombre'].lower()).first()
        j2 = db.query(Jugador).filter(func.lower(Jugador.nombre) == p['j2_nombre'].lower()).first()
        if j1 and j2:
            db.add(Partido(
                jugador_1_id=j1.id, jugador_1_nombre=j1.nombre,
                jugador_2_id=j2.id, jugador_2_nombre=j2.nombre,
                cancha=str(p.get('cancha', '1')), hora=str(p.get('hora', 'Por definir')),
                estado="pendiente"
            ))
            creados += 1
    db.commit()
    guardar_noticia(db, "¡PROGRAMACIÓN LISTA!", f"Se han generado {creados} nuevos partidos. Revisa tu horario.", "anuncio")
    return f"✅ Fixture creado ({creados} partidos)."

def ejecutar_victoria_ia(db: Session, nombre_ganador: str, nombre_perdedor: str, puntos_ganados: int, puntos_perdidos: int, marcador: str, titulo_noticia: str, cuerpo_noticia: str):
    """
    Guarda el resultado Y la noticia periodística.
    """
    ganador = db.query(Jugador).filter(func.lower(Jugador.nombre) == nombre_ganador.lower()).first()
    perdedor = db.query(Jugador).filter(func.lower(Jugador.nombre) == nombre_perdedor.lower()).first()
    
    if not ganador or not perdedor: return "❌ Error: Jugadores no encontrados."

    # Puntos
    ganador.puntos += puntos_ganados
    perdedor.puntos = max(0, perdedor.puntos - puntos_perdidos)
    ganador.victorias += 1
    perdedor.derrotas += 1
    
    # Cerrar partido
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
        # Partido Reto
        db.add(Partido(
            jugador_1_id=ganador.id, jugador_1_nombre=ganador.nombre,
            jugador_2_id=perdedor.id, jugador_2_nombre=perdedor.nombre,
            ganador_id=ganador.id, marcador=marcador, estado="finalizado",
            cancha="Reto", hora=datetime.now().strftime("%I:%M %p")
        ))

    # GUARDAR LA NOTICIA DEL PERIODISTA
    guardar_noticia(db, titulo_noticia, cuerpo_noticia, "partido")

    db.commit()
    return "OK"

# --- CONSULTAS ---
def obtener_estado_torneo(db: Session):
    total = db.query(Jugador).count()
    # Mostramos la última noticia
    ultima = db.query(Noticia).order_by(Noticia.id.desc()).first()
    news = f"📰 *ÚLTIMA HORA:* {ultima.titulo}" if ultima else ""
    return f"📊 *Estado*\n👥 Inscritos: {total}\n{news}"

def consultar_proximo_partido(db: Session, celular: str):
    # (Misma lógica de búsqueda familiar)
    mis = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis: return "No tienes inscritos."
    ids = [p.id for p in mis]
    parts = db.query(Partido).filter((Partido.jugador_1_id.in_(ids)) | (Partido.jugador_2_id.in_(ids)), Partido.estado == "pendiente").all()
    if not parts: return "📅 No tienes partidos."
    resp = "📅 **TUS PARTIDOS:**\n"
    for p in parts:
        mi = next((j for j in mis if j.id in [p.jugador_1_id, p.jugador_2_id]), None)
        riv = p.jugador_2_nombre if p.jugador_1_id == mi.id else p.jugador_1_nombre
        resp += f"\n👤 **{mi.nombre}** VS {riv}\n⏰ {p.hora} | 🏟️ {p.cancha}\n"
    return resp

def registrar_victoria(db: Session, celular: str, nombre_ganador_detectado: str, nombre_perfil_wa: str, s1: int, s2: int):
    # Esta función ahora es solo un wrapper para la IA, idealmente no se usa directamente
    return "Usa la IA para reportar."

# Compatibilidad
def guardar_configuracion_ia(db: Session, k, v): set_config_value(db, k, v); return "Ok"
def actualizar_configuracion(db, k, v): return guardar_configuracion_ia(db, k, v)
def enviar_difusion_masiva(db, m): return "Difusión enviada."
def procesar_organizacion_torneo(db, m): return "Usa el comando 'Organizar torneo'."
def generar_partidos_automaticos(db): return "Usa la IA."