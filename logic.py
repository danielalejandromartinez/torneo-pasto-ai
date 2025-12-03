from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Jugador, Partido, Configuracion
import random
import os
import requests
from datetime import datetime, timedelta

# ==========================================
# 🛠️ HERRAMIENTAS DE SISTEMA Y ADMIN
# ==========================================

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

def actualizar_configuracion(db: Session, clave: str, valor: str):
    set_config(db, clave, valor)
    return f"🫡 Listo jefe. Configurado: **{clave}** = **{valor}**."

def obtener_configuracion(db: Session):
    configs = db.query(Configuracion).all()
    texto = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    return texto if texto else "No hay reglas definidas aún."

def enviar_difusion_masiva(db: Session, mensaje: str):
    jugadores = db.query(Jugador.celular).distinct().all()
    if not jugadores: return "No hay jugadores inscritos."
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

# ==========================================
# 🧠 CONTEXTO PARA EL AGENTE AUTÓNOMO (NECESARIO PARA MAIN.PY)
# ==========================================

def obtener_contexto_ranking(db: Session):
    """Le da a la IA la foto del ranking para que tome decisiones"""
    jugadores = db.query(Jugador).order_by(Jugador.puntos.desc()).all()
    resumen = "🏆 **RANKING ACTUAL:**\n"
    for i, j in enumerate(jugadores):
        posicion = i + 1
        zona = "BRONCE"
        if posicion <= 5: zona = "ORO"
        elif posicion <= 20: zona = "PLATA"
        resumen += f"#{posicion} {j.nombre} ({j.celular}) - {j.puntos} pts - ZONA {zona}\n"
    
    configs = db.query(Configuracion).all()
    reglas = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    return f"{resumen}\n📜 **REGLAS:**\n{reglas}"

# ==========================================
# 🧙‍♂️ WIZARD DE ORGANIZACIÓN
# ==========================================

def procesar_organizacion_torneo(db: Session, mensaje_usuario: str):
    paso_actual = get_config(db, "wizard_paso")
    
    if mensaje_usuario.lower() in ["cancelar", "salir", "abortar"]:
        set_config(db, "wizard_paso", "")
        return "🛑 Configuración cancelada."

    if not paso_actual or mensaje_usuario.lower() in ["organizar torneo", "iniciar wizard", "configurar torneo"]:
        set_config(db, "wizard_paso", "canchas")
        return "👷‍♂️ ¡Listo Jefe! (Escribe 'Cancelar' para salir).\n\n1️⃣ **¿Cuántas canchas?** (Ej: 2)"

    if paso_actual == "canchas":
        if not mensaje_usuario.isdigit(): return "⚠️ Solo números."
        set_config(db, "num_canchas", mensaje_usuario)
        set_config(db, "wizard_paso", "duracion")
        return f"✅ {mensaje_usuario} canchas.\n\n2️⃣ **¿Duración mins?** (Ej: 30)"

    if paso_actual == "duracion":
        if not mensaje_usuario.isdigit(): return "⚠️ Solo números."
        set_config(db, "duracion_partido", mensaje_usuario)
        set_config(db, "wizard_paso", "hora")
        return f"✅ {mensaje_usuario} mins.\n\n3️⃣ **¿Hora inicio?** (Ej: 15:00)"

    if paso_actual == "hora":
        if ":" not in mensaje_usuario: return "⚠️ Formato HH:MM."
        set_config(db, "hora_inicio", mensaje_usuario)
        set_config(db, "wizard_paso", "confirmar")
        return f"📋 Resumen listo. Escribe **GENERAR** para confirmar."

    if paso_actual == "confirmar":
        if "generar" in mensaje_usuario.lower():
            set_config(db, "wizard_paso", "") 
            return generar_partidos_automaticos(db)
        return "Escribe GENERAR o 'Cancelar'."

    return "No entendí. Escribe 'Organizar torneo'."

# ==========================================
# 🎾 LÓGICA DEL JUEGO
# ==========================================

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
    jugadores = db.query(Jugador).all()
    if len(jugadores) < 2: return "❌ Faltan jugadores."
    db.query(Partido).filter(Partido.estado == "pendiente").delete()
    random.shuffle(jugadores)
    try:
        num_canchas = int(get_config(db, "num_canchas") or 1)
        duracion = int(get_config(db, "duracion_partido") or 30)
        hora_str = get_config(db, "hora_inicio") or "12:00"
        hora_base = datetime.strptime(hora_str, "%H:%M")
        ahora = datetime.now()
        hora_base = hora_base.replace(year=ahora.year, month=ahora.month, day=ahora.day)
    except: return "⚠️ Error config. Usa el comando 'Organizar torneo'."

    creados = 0; cancha_actual = 1; slot_tiempo = 0
    for i in range(len(jugadores) // 2):
        p1, p2 = jugadores[i*2], jugadores[i*2+1]
        mins = slot_tiempo * duracion
        hora = (hora_base + timedelta(minutes=mins)).strftime("%I:%M %p")
        db.add(Partido(jugador_1_id=p1.id, jugador_1_nombre=p1.nombre, jugador_2_id=p2.id, jugador_2_nombre=p2.nombre, cancha=str(cancha_actual), hora=hora, estado="pendiente"))
        creados += 1
        if cancha_actual < num_canchas: cancha_actual += 1
        else: cancha_actual = 1; slot_tiempo += 1
    db.commit()
    return f"✅ **¡FIXTURE LISTO!**\n{creados} partidos creados."

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
        resp += f"\n👤 **{mi_jug.nombre}** VS {rival}\n⏰ {p.hora} | 🏟️ C-{p.cancha}\n"
    return resp

def registrar_victoria(db: Session, celular: str, nombre_ganador_detectado: str, nombre_perfil_wa: str, s1: int, s2: int):
    # Lógica estándar de victoria (por si acaso se usa en main antiguo)
    return ejecutar_victoria_ia(db, nombre_ganador_detectado, "Rival Desconocido", 10, 10, f"{s1}-{s2}")

# --- LA FUNCIÓN QUE FALTABA (EJECUCIÓN IA) ---
def ejecutar_victoria_ia(db: Session, nombre_ganador: str, nombre_perdedor: str, puntos_ganados: int, puntos_perdidos: int, marcador: str):
    """
    Esta función obedece ciegamente a la IA para aplicar puntos y cerrar partidos.
    """
    ganador = db.query(Jugador).filter(func.lower(Jugador.nombre) == nombre_ganador.lower()).first()
    perdedor = db.query(Jugador).filter(func.lower(Jugador.nombre) == nombre_perdedor.lower()).first()
    
    if not ganador or not perdedor:
        return f"❌ Error: No encontré a {nombre_ganador} o {nombre_perdedor} en la BD."

    # Aplicar puntos
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
        # Partido "Reto" (Callejero)
        db.add(Partido(
            jugador_1_id=ganador.id, jugador_1_nombre=ganador.nombre,
            jugador_2_id=perdedor.id, jugador_2_nombre=perdedor.nombre,
            ganador_id=ganador.id, marcador=marcador, estado="finalizado",
            cancha="Reto", hora=datetime.now().strftime("%I:%M %p")
        ))

    db.commit()
    return "OK"