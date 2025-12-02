from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Jugador, Partido, Configuracion
import random
import os
import requests
from datetime import datetime, timedelta

# --- HERRAMIENTAS DE CONFIGURACIÓN ---
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

# --- PARA COMPATIBILIDAD CON MAIN.PY ---
def actualizar_configuracion(db: Session, clave: str, valor: str):
    set_config(db, clave, valor)
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

# --- MÁQUINA DE ESTADOS (WIZARD DE ORGANIZACIÓN) ---
# ESTA ES LA FUNCIÓN QUE FALTABA
def procesar_organizacion_torneo(db: Session, mensaje_usuario: str):
    paso_actual = get_config(db, "wizard_paso")
    
    # INICIO
    if not paso_actual or mensaje_usuario.lower() in ["organizar torneo", "iniciar wizard", "configurar torneo"]:
        set_config(db, "wizard_paso", "canchas")
        return "👷‍♂️ ¡Listo Jefe! Configuremos el torneo.\n\n1️⃣ **¿Cuántas canchas** tenemos? (Ej: 2)"

    # PASO 1: CANCHAS
    if paso_actual == "canchas":
        if not mensaje_usuario.isdigit(): return "⚠️ Escribe solo el número (Ej: 2)."
        set_config(db, "num_canchas", mensaje_usuario)
        set_config(db, "wizard_paso", "duracion")
        return f"✅ {mensaje_usuario} canchas.\n\n2️⃣ **¿Duración del partido** en minutos? (Ej: 30)"

    # PASO 2: DURACIÓN
    if paso_actual == "duracion":
        if not mensaje_usuario.isdigit(): return "⚠️ Escribe solo minutos (Ej: 30)."
        set_config(db, "duracion_partido", mensaje_usuario)
        set_config(db, "wizard_paso", "hora")
        return f"✅ {mensaje_usuario} mins.\n\n3️⃣ **¿Hora de inicio**? (Formato 24h, Ej: 15:00)"

    # PASO 3: HORA
    if paso_actual == "hora":
        if ":" not in mensaje_usuario: return "⚠️ Usa formato hora (Ej: 15:00)."
        set_config(db, "hora_inicio", mensaje_usuario)
        set_config(db, "wizard_paso", "confirmar")
        canchas = get_config(db, "num_canchas")
        duracion = get_config(db, "duracion_partido")
        return (f"📋 **RESUMEN:**\n- Canchas: {canchas}\n- Duración: {duracion} min\n- Inicio: {mensaje_usuario}\n\nEscribe **GENERAR** para confirmar.")

    # PASO 4: GENERAR
    if paso_actual == "confirmar":
        if "generar" in mensaje_usuario.lower():
            set_config(db, "wizard_paso", "") 
            return generar_partidos_automaticos(db) # Usamos la función principal
        else:
            return "Escribe **GENERAR** para confirmar o 'Organizar torneo' para reiniciar."

    return "No entendí. Escribe 'Organizar torneo' para reiniciar."

# --- LÓGICA DEL JUEGO ---

def inscribir_jugador(db: Session, nombre: str, celular: str):
    existente = db.query(Jugador).filter(Jugador.celular == celular, func.lower(Jugador.nombre) == nombre.lower()).first()
    if existente: return f"⚠️ {existente.nombre} ya está inscrito."
    db.add(Jugador(nombre=nombre, celular=celular, puntos=100))
    db.commit()
    total = db.query(Jugador).filter(Jugador.celular == celular).count()
    return f"✅ Inscrito: **{nombre}**. Gestionas {total} perfiles."

def obtener_estado_torneo(db: Session):
    total = db.query(Jugador).count()
    info = obtener_configuracion(db)
    return f"📊 *Estado*\n👥 Inscritos: {total}\nℹ️ {info}"

def generar_partidos_automaticos(db: Session):
    # Esta función ahora usa la configuración de la base de datos
    jugadores = db.query(Jugador).all()
    if len(jugadores) < 2: return "❌ Faltan jugadores."
    
    db.query(Partido).filter(Partido.estado == "pendiente").delete()
    random.shuffle(jugadores)
    
    # Intentamos leer config, si falla usamos defaults
    try:
        num_canchas = int(get_config(db, "num_canchas") or 1)
        duracion = int(get_config(db, "duracion_partido") or 30)
        hora_str = get_config(db, "hora_inicio") or "12:00"
        hora_base = datetime.strptime(hora_str, "%H:%M")
        ahora = datetime.now()
        hora_base = hora_base.replace(year=ahora.year, month=ahora.month, day=ahora.day)
    except:
        return "⚠️ Error de configuración. Usa el comando 'Organizar torneo' primero."

    creados = 0
    cancha_actual = 1
    slot_tiempo = 0
    
    # Emparejamiento simple
    num_matches = len(jugadores) // 2
    
    for i in range(num_matches):
        p1 = jugadores[i*2]
        p2 = jugadores[i*2+1]
        
        minutos_sumar = slot_tiempo * duracion
        hora_partido = hora_base + timedelta(minutes=minutos_sumar)
        
        nuevo = Partido(
            jugador_1_id=p1.id, jugador_1_nombre=p1.nombre,
            jugador_2_id=p2.id, jugador_2_nombre=p2.nombre,
            cancha=str(cancha_actual),
            hora=hora_partido.strftime("%I:%M %p"),
            estado="pendiente"
        )
        db.add(nuevo)
        creados += 1
        
        if cancha_actual < num_canchas:
            cancha_actual += 1
        else:
            cancha_actual = 1
            slot_tiempo += 1
            
    db.commit()
    return f"✅ **¡FIXTURE GENERADO!**\n{creados} partidos creados.\nRevisa la web."

def consultar_proximo_partido(db: Session, celular: str):
    mis_jugadores = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis_jugadores: return "No tienes inscritos."
    ids = [p.id for p in mis_jugadores]
    partidos = db.query(Partido).filter((Partido.jugador_1_id.in_(ids)) | (Partido.jugador_2_id.in_(ids)), Partido.estado == "pendiente").all()
    if not partidos: return "📅 No tienes partidos programados."
    resp = "📅 **TUS PARTIDOS:**\n"
    for p in partidos:
        mi_jug = next((j for j in mis_jugadores if j.id in [p.jugador_1_id, p.jugador_2_id]), None)
        rival = p.jugador_2_nombre if p.jugador_1_id == mi_jug.id else p.jugador_1_nombre
        resp += f"\n👤 **{mi_jug.nombre}** VS {rival}\n⏰ {p.hora} | 🏟️ C-{p.cancha}\n"
    return resp

def registrar_victoria(db: Session, celular: str, nombre_ganador_detectado: str, sets_ganador: int, sets_perdedor: int):
    # (Manteniendo la lógica que ya funcionaba)
    mis_jugadores = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis_jugadores: return "No tienes perfiles."
    ids_jugadores = [p.id for p in mis_jugadores]
    partidos = db.query(Partido).filter((Partido.jugador_1_id.in_(ids_jugadores)) | (Partido.jugador_2_id.in_(ids_jugadores)), Partido.estado == "pendiente").all()
    if not partidos: return "No tienes partidos pendientes."
    
    partido_objetivo = None
    mi_jugador_ganador = None
    
    if len(partidos) == 1:
        partido_objetivo = partidos[0]
        mi_jugador_ganador = db.query(Jugador).get(partido_objetivo.jugador_1_id if partido_objetivo.jugador_1_id in ids_jugadores else partido_objetivo.jugador_2_id)
    else:
        if not nombre_ganador_detec