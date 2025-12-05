from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Jugador, Partido, Configuracion, Noticia
import random
import os
import requests
from datetime import datetime, timedelta

# --- MEMORIA (CONFIGURACIÓN) ---
def get_config_value(db: Session, key: str):
    item = db.query(Configuracion).filter(Configuracion.key == key).first()
    return item.value if item else None

def set_config_value(db: Session, key: str, value: str):
    item = db.query(Configuracion).filter(Configuracion.key == key).first()
    if not item: db.add(Configuracion(key=key, value=value))
    else: item.value = value
    db.commit()

# --- OJOS DE LA IA (CONTEXTO) ---
def obtener_contexto_completo(db: Session):
    """
    Entrega toda la información necesaria para que la IA tome decisiones expertas.
    """
    # 1. Jugadores Ordenados (Para que la IA sepa quién es el #1)
    jugadores = db.query(Jugador).order_by(Jugador.puntos.desc()).all()
    lista_jugadores = "\n".join([f"- {j.nombre} ({j.puntos} pts)" for j in jugadores])
    if not lista_jugadores: lista_jugadores = "Ninguno"
    
    # 2. Configuración Técnica
    configs = db.query(Configuracion).all()
    lista_config = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    
    # 3. Partidos Actuales (Para no programar sobre lo programado)
    partidos = db.query(Partido).filter(Partido.estado == "pendiente").all()
    lista_partidos = "\n".join([f"- {p.jugador_1_nombre} vs {p.jugador_2_nombre} ({p.hora})" for p in partidos])
    
    return f"""
    === DATOS DEL CLUB ===
    JUGADORES (Ranking Actual):
    {lista_jugadores}
    
    CONFIGURACIÓN TÉCNICA:
    {lista_config}
    
    PARTIDOS YA PROGRAMADOS:
    {lista_partidos}
    ======================
    """

def guardar_noticia(db: Session, titulo: str, cuerpo: str, tipo: str="general"):
    try:
        db.add(Noticia(titulo=titulo, cuerpo=cuerpo, tipo=tipo))
        db.commit()
    except: pass

# --- HERRAMIENTAS DE EJECUCIÓN (LA IA ORDENA, PYTHON ESCRIBE) ---

def guardar_organizacion_experta(db: Session, lista_partidos: list):
    """
    Recibe el plan maestro de la IA y lo guarda en la BD.
    """
    # Limpiamos lo pendiente anterior
    db.query(Partido).filter(Partido.estado == "pendiente").delete()
    
    creados = 0
    for p in lista_partidos:
        # Buscamos jugadores (insensible a mayúsculas)
        j1 = db.query(Jugador).filter(func.lower(Jugador.nombre) == p['j1_nombre'].lower()).first()
        j2 = db.query(Jugador).filter(func.lower(Jugador.nombre) == p['j2_nombre'].lower()).first()
        
        if j1 and j2:
            db.add(Partido(
                jugador_1_id=j1.id, jugador_1_nombre=j1.nombre,
                jugador_2_id=j2.id, jugador_2_nombre=j2.nombre,
                cancha=str(p.get('cancha', '1')),
                hora=str(p.get('hora', 'Por definir')),
                estado="pendiente"
            ))
            creados += 1
            
    db.commit()
    guardar_noticia(db, "¡FIXTURE OFICIAL PUBLICADO!", f"El Director Deportivo ha generado {creados} cruces de alto nivel. ¡Revisen programación!", "anuncio")
    return f"✅ **ORGANIZACIÓN COMPLETADA**\nHe diseñado y guardado {creados} partidos estratégicos.\n🔗 Ver en web: https://torneo-pasto-ai.onrender.com/programacion"

def guardar_configuracion_ia(db: Session, clave: str, valor: str):
    set_config_value(db, clave, valor)
    return f"📝 Dato técnico guardado: **{clave}** = **{valor}**."

# --- ACCIONES DE JUGADOR ---

def inscribir_jugador(db: Session, nombre: str, celular: str):
    existente = db.query(Jugador).filter(Jugador.celular == celular, func.lower(Jugador.nombre) == nombre.lower()).first()
    if existente: return f"⚠️ **{existente.nombre}** ya está inscrito."
    
    db.add(Jugador(nombre=nombre, celular=celular, puntos=100))
    db.commit()
    
    total = db.query(Jugador).filter(Jugador.celular == celular).count()
    guardar_noticia(db, "NUEVO FICHAJE", f"{nombre} entra al ranking.", "anuncio")
    return f"✅ Inscrito: **{nombre}**. (Perfil #{total})."

def consultar_proximo_partido(db: Session, celular: str):
    mis = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis: return "No tienes perfiles inscritos."
    ids = [p.id for p in mis]
    parts = db.query(Partido).filter((Partido.jugador_1_id.in_(ids)) | (Partido.jugador_2_id.in_(ids)), Partido.estado == "pendiente").all()
    if not parts: return "📅 No tienes partidos programados."
    
    resp = "📅 **TUS PARTIDOS:**\n"
    for p in parts:
        mi = next((j for j in mis if j.id in [p.jugador_1_id, p.jugador_2_id]), None)
        riv = p.jugador_2_nombre if p.jugador_1_id == mi.id else p.jugador_1_nombre
        resp += f"\n👤 **{mi.nombre}** VS {riv}\n⏰ {p.hora} | 🏟️ {p.cancha}\n"
    return resp

def obtener_estado_torneo(db: Session):
    jugadores = db.query(Jugador).all()
    if not jugadores: return "Sin inscritos."
    lista = "\n".join([f"• {j.nombre}" for j in jugadores])
    return f"📊 **LISTA DE JUGADORES ({len(jugadores)}):**\n{lista}\n\n🔗 Web: https://torneo-pasto-ai.onrender.com"

def ejecutar_victoria_ia(db: Session, nombre_ganador: str, nombre_perdedor: str, puntos_ganados: int, puntos_perdidos: int, marcador: str, titulo_noticia: str, cuerpo_noticia: str):
    ganador = db.query(Jugador).filter(func.lower(Jugador.nombre) == nombre_ganador.lower()).first()
    perdedor = db.query(Jugador).filter(func.lower(Jugador.nombre) == nombre_perdedor.lower()).first()
    
    if not ganador or not perdedor: return "❌ Error: No encontré esos nombres. Revisa la ortografía."

    # Lógica de puntos
    ganador.puntos += puntos_ganados
    perdedor.puntos = max(0, perdedor.puntos - puntos_perdidos)
    ganador.victorias += 1
    perdedor.derrotas += 1
    
    # Cerrar partido
    partido = db.query(Partido).filter((Partido.estado == "pendiente"), (Partido.jugador_1_id.in_([ganador.id, perdedor.id])), (Partido.jugador_2_id.in_([ganador.id, perdedor.id]))).first()
    
    if partido:
        partido.estado = "finalizado"
        partido.ganador_id = ganador.id
        partido.marcador = marcador
    else:
        # Reto libre
        db.add(Partido(jugador_1_id=ganador.id, jugador_1_nombre=ganador.nombre, jugador_2_id=perdedor.id, jugador_2_nombre=perdedor.nombre, ganador_id=ganador.id, marcador=marcador, estado="finalizado", cancha="Reto", hora=datetime.now().strftime("%I:%M %p")))

    guardar_noticia(db, titulo_noticia, cuerpo_noticia, "partido")
    db.commit()
    return "OK"

# Alias para main
def registrar_victoria(db, c, ng, nw, s1, s2): return "Usa la IA."
def generar_partidos_automaticos(db): return "Usa la IA."
def procesar_organizacion_torneo(db, m): return "Usa la IA."