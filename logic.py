from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Jugador, Partido, Configuracion
import random
import os
import requests
from datetime import datetime, timedelta

# --- HERRAMIENTAS CONFIG ---
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

def actualizar_configuracion(db: Session, clave: str, valor: str):
    set_config_value(db, clave, valor)
    return f"🫡 Configurado: **{clave}** = **{valor}**."

def obtener_configuracion(db: Session):
    configs = db.query(Configuracion).all()
    texto = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    return texto if texto else "No hay reglas definidas aún."

def enviar_difusion_masiva(db: Session, mensaje: str):
    jugadores = db.query(Jugador.celular).distinct().all()
    if not jugadores: return "No hay nadie inscrito."
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    count = 0
    for j in jugadores:
        try:
            data = {"messaging_product": "whatsapp", "to": j.celular, "type": "text", "text": {"body": f"📢 *ANUNCIO*\n\n{mensaje}\n\n_Pasto.AI_"}}
            requests.post(url, headers=headers, json=data)
            count += 1
        except: continue
    return f"✅ Enviado a {count} números únicos."

# --- CONTEXTO PARA IA ---
def obtener_contexto_completo(db: Session):
    jugadores = db.query(Jugador).all()
    lista_jugadores = "\n".join([f"- {j.nombre} ({j.celular})" for j in jugadores])
    if not lista_jugadores: lista_jugadores = "Ninguno"
    configs = db.query(Configuracion).all()
    lista_config = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    return f"--- DATA ---\nINSCRITOS:\n{lista_jugadores}\nREGLAS:\n{lista_config}\n------------"

# --- BRAZOS EJECUTORES IA ---
def guardar_configuracion_ia(db: Session, clave: str, valor: str):
    set_config_value(db, clave, valor)
    return f"📝 Guardé: **{clave}** = **{valor}**."

def guardar_organizacion_ia(db: Session, lista_partidos: list):
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
    return f"✅ **¡FIXTURE IA CREADO!**\n{creados} partidos listos."

# --- HERRAMIENTAS MANUALES / WIZARD ---
def generar_partidos_automaticos(db: Session):
    jugadores = db.query(Jugador).all()
    if len(jugadores) < 2: return "❌ Faltan jugadores."
    db.query(Partido).filter(Partido.estado == "pendiente").delete()
    random.shuffle(jugadores)
    try:
        duracion = int(get_config_value(db, "duracion_partido") or 30)
        hora_str = get_config_value(db, "hora_inicio") or "12:00"
        hora_base = datetime.strptime(hora_str, "%H:%M").replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
    except: return "⚠️ Error config."
    
    creados = 0
    for i in range(len(jugadores) // 2):
        p1, p2 = jugadores[i*2], jugadores[i*2+1]
        hora = (hora_base + timedelta(minutes=i*duracion)).strftime("%I:%M %p")
        db.add(Partido(jugador_1_id=p1.id, jugador_1_nombre=p1.nombre, jugador_2_id=p2.id, jugador_2_nombre=p2.nombre, cancha="1", hora=hora, estado="pendiente"))
        creados += 1
    db.commit()
    return f"✅ Fixture Manual: {creados} partidos."

def procesar_organizacion_torneo(db: Session, mensaje: str):
    return generar_partidos_automaticos(db)

# --- JUGADORES Y RESULTADOS ---
def inscribir_jugador(db: Session, nombre: str, celular: str):
    existente = db.query(Jugador).filter(Jugador.celular == celular, func.lower(Jugador.nombre) == nombre.lower()).first()
    if existente: return f"⚠️ {existente.nombre} ya está inscrito."
    db.add(Jugador(nombre=nombre, celular=celular, puntos=100))
    db.commit()
    return f"✅ Inscrito: **{nombre}**."

def obtener_estado_torneo(db: Session):
    total = db.query(Jugador).count()
    return f"👥 Total Inscritos: {total}"

def consultar_proximo_partido(db: Session, celular: str):
    mis = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis: return "No tienes inscritos."
    ids = [p.id for p in mis]
    parts = db.query(Partido).filter((Partido.jugador_1_id.in_(ids)) | (Partido.jugador_2_id.in_(ids)), Partido.estado == "pendiente").all()
    if not parts: return "📅 Sin partidos."
    resp = "📅 **TUS PARTIDOS:**\n"
    for p in parts:
        mi = next((j for j in mis if j.id in [p.jugador_1_id, p.jugador_2_id]), None)
        riv = p.jugador_2_nombre if p.jugador_1_id == mi.id else p.jugador_1_nombre
        resp += f"\n👤 **{mi.nombre}** VS {riv}\n⏰ {p.hora} | 🏟️ {p.cancha}\n"
    return resp

def registrar_victoria(db: Session, celular: str, nombre_ganador: str, nombre_wa: str, s1: int, s2: int):
    mis = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis: return "No tienes perfiles."
    ids = [p.id for p in mis]
    parts = db.query(Partido).filter((Partido.jugador_1_id.in_(ids)) | (Partido.jugador_2_id.in_(ids)), Partido.estado == "pendiente").all()
    if not parts: return "Sin partidos pendientes."
    
    objetivo = None
    ganador = None
    candidato = nombre_ganador if nombre_ganador else nombre_wa
    
    if len(parts) == 1:
        objetivo = parts[0]
        ganador = db.query(Jugador).get(objetivo.jugador_1_id if objetivo.jugador_1_id in ids else objetivo.jugador_2_id)
    else:
        for p in parts:
            j1 = db.query(Jugador).get(p.jugador_1_id)
            j2 = db.query(Jugador).get(p.jugador_2_id)
            if candidato and candidato.lower() in j1.nombre.lower() and j1.id in ids:
                objetivo = p; ganador = j1; break
            elif candidato and candidato.lower() in j2.nombre.lower() and j2.id in ids:
                objetivo = p; ganador = j2; break
        if not objetivo: return f"❌ No encontré partido para **{candidato}**."

    perdedor_id = objetivo.jugador_2_id if objetivo.jugador_1_id == ganador.id else objetivo.jugador_1_id
    perdedor = db.query(Jugador).get(perdedor_id)
    
    ganador.puntos += 10
    perdedor.puntos = max(0, perdedor.puntos - 10)
    ganador.victorias += 1; perdedor.derrotas += 1
    objetivo.estado = "finalizado"; objetivo.ganador_id = ganador.id; objetivo.marcador = f"{s1}-{s2}"
    db.commit()
    return f"🏆 **¡VICTORIA!**\nGanador: {ganador.nombre}\nRanking actualizado."