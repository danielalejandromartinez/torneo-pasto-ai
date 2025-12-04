from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Jugador, Partido, Configuracion, Noticia
import random
import os
import requests
from datetime import datetime, timedelta

# ==========================================
# 🛠️ HERRAMIENTAS DE MEMORIA (CONFIGURACIÓN)
# ==========================================

def get_config_value(db: Session, key: str):
    """Obtiene un valor de la configuración interna"""
    item = db.query(Configuracion).filter(Configuracion.key == key).first()
    return item.value if item else None

def set_config_value(db: Session, key: str, value: str):
    """Guarda un valor en la configuración interna"""
    item = db.query(Configuracion).filter(Configuracion.key == key).first()
    if not item:
        item = Configuracion(key=key, value=value)
        db.add(item)
    else:
        item.value = value
    db.commit()

# Funciones puente para compatibilidad
def actualizar_configuracion(db: Session, clave: str, valor: str):
    set_config_value(db, clave, valor)
    return f"🫡 Configurado: **{clave}** = **{valor}**."

def obtener_configuracion(db: Session):
    configs = db.query(Configuracion).all()
    texto = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    return texto if texto else "No hay reglas definidas aún."

def enviar_difusion_masiva(db: Session, mensaje: str):
    """Envía mensaje a todos los celulares únicos"""
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

# ==========================================
# 🧠 CONTEXTO Y NOTICIAS
# ==========================================

def obtener_contexto_completo(db: Session):
    """Le da a la IA la foto completa: Jugadores + Reglas"""
    jugadores = db.query(Jugador).order_by(Jugador.puntos.desc()).all()
    lista_jugadores = "\n".join([f"- {j.nombre} ({j.puntos} pts)" for j in jugadores])
    if not lista_jugadores: lista_jugadores = "Ninguno"
    
    configs = db.query(Configuracion).all()
    lista_config = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    
    return f"--- DATA ACTUAL ---\nINSCRITOS:\n{lista_jugadores}\nREGLAS:\n{lista_config}\n-------------------"

def guardar_noticia(db: Session, titulo: str, cuerpo: str, tipo: str="general"):
    """Guarda un titular para la web"""
    try:
        nueva = Noticia(titulo=titulo, cuerpo=cuerpo, tipo=tipo)
        db.add(nueva)
        db.commit()
    except: pass

# ==========================================
# 🧙‍♂️ WIZARD DE ORGANIZACIÓN (EL PASO A PASO)
# ==========================================

def procesar_organizacion_torneo(db: Session, mensaje_usuario: str):
    """Máquina de estados para configurar el torneo paso a paso"""
    paso_actual = get_config_value(db, "wizard_paso")
    
    # Cancelar
    if mensaje_usuario.lower() in ["cancelar", "salir", "abortar", "basta"]:
        set_config_value(db, "wizard_paso", "")
        return "🛑 Configuración cancelada. ¿En qué más te ayudo?"

    # Inicio
    if not paso_actual or mensaje_usuario.lower() in ["organizar torneo", "iniciar wizard", "configurar torneo"]:
        set_config_value(db, "wizard_paso", "canchas")
        return "👷‍♂️ ¡Listo Jefe! (Escribe 'Cancelar' para salir).\n\n1️⃣ **¿Cuántas canchas** tenemos disponibles? (Ej: 2)"

    # Paso 1: Canchas
    if paso_actual == "canchas":
        if not mensaje_usuario.isdigit(): return "⚠️ Escribe solo el número (Ej: 2)."
        set_config_value(db, "num_canchas", mensaje_usuario)
        set_config_value(db, "wizard_paso", "duracion")
        return f"✅ {mensaje_usuario} canchas.\n\n2️⃣ **¿Duración del partido** en minutos? (Ej: 30)"

    # Paso 2: Duración
    if paso_actual == "duracion":
        if not mensaje_usuario.isdigit(): return "⚠️ Escribe solo minutos (Ej: 30)."
        set_config_value(db, "duracion_partido", mensaje_usuario)
        set_config_value(db, "wizard_paso", "hora")
        return f"✅ {mensaje_usuario} mins.\n\n3️⃣ **¿Hora de inicio**? (Formato 24h, Ej: 15:00)"

    # Paso 3: Hora
    if paso_actual == "hora":
        if ":" not in mensaje_usuario: return "⚠️ Usa formato hora (Ej: 15:00)."
        set_config_value(db, "hora_inicio", mensaje_usuario)
        set_config_value(db, "wizard_paso", "confirmar")
        return f"📋 Resumen listo. Escribe **GENERAR** para confirmar."

    # Paso 4: Confirmar
    if paso_actual == "confirmar":
        if "generar" in mensaje_usuario.lower():
            set_config_value(db, "wizard_paso", "") 
            return generar_partidos_automaticos(db)
        return "Escribe GENERAR o 'Cancelar'."

    return "No entendí. Escribe 'Organizar torneo' para reiniciar."

# ==========================================
# 🧠 BRAZOS EJECUTORES IA (AUTONOMÍA)
# ==========================================

def guardar_configuracion_ia(db: Session, clave: str, valor: str):
    set_config_value(db, clave, valor)
    return f"📝 Guardé: **{clave}** = **{valor}**."

def guardar_organizacion_ia(db: Session, lista_partidos: list):
    """La IA generó el cuadro, aquí lo guardamos."""
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
    # Guardamos la noticia
    guardar_noticia(db, "¡PROGRAMACIÓN LISTA!", f"Se han generado {creados} nuevos partidos. Revisa tu horario.", "anuncio")
    return f"✅ **¡FIXTURE IA CREADO!**\n{creados} partidos listos.\nRevisa la web: https://torneo-pasto-ai.onrender.com/programacion"

# Función manual de respaldo
def generar_partidos_automaticos(db: Session):
    jugadores = db.query(Jugador).all()
    if len(jugadores) < 2: return "❌ Faltan jugadores."
    db.query(Partido).filter(Partido.estado == "pendiente").delete()
    random.shuffle(jugadores)
    
    try:
        num_canchas = int(get_config_value(db, "num_canchas") or 1)
        duracion = int(get_config_value(db, "duracion_partido") or 30)
        hora_str = get_config_value(db, "hora_inicio") or "12:00"
        hora_base = datetime.strptime(hora_str, "%H:%M")
        ahora = datetime.now()
        hora_base = hora_base.replace(year=ahora.year, month=ahora.month, day=ahora.day)
    except:
        return "⚠️ Error leyendo configuración. Usa el comando 'Organizar torneo' primero."

    creados = 0; cancha_actual = 1; slot_tiempo = 0
    for i in range(len(jugadores) // 2):
        p1, p2 = jugadores[i*2], jugadores[i*2+1]
        mins = slot_tiempo * duracion
        hora = (hora_base + timedelta(minutes=mins)).strftime("%I:%M %p")
        db.add(Partido(
            jugador_1_id=p1.id, jugador_1_nombre=p1.nombre,
            jugador_2_id=p2.id, jugador_2_nombre=p2.nombre,
            cancha=str(cancha_actual), hora=hora, estado="pendiente"
        ))
        creados += 1
        if cancha_actual < num_canchas: cancha_actual += 1
        else: cancha_actual = 1; slot_tiempo += 1
            
    db.commit()
    guardar_noticia(db, "¡PROGRAMACIÓN LISTA!", f"Fixture generado manual: {creados} partidos.", "anuncio")
    return f"✅ **¡FIXTURE GENERADO!**\n{creados} partidos creados."

# ==========================================
# 👥 LÓGICA DE JUGADORES Y RESULTADOS
# ==========================================

def inscribir_jugador(db: Session, nombre: str, celular: str):
    # Lógica Familiar: Verifica si el nombre existe en este celular
    existente = db.query(Jugador).filter(
        Jugador.celular == celular, 
        func.lower(Jugador.nombre) == nombre.lower()
    ).first()
    
    if existente: 
        return f"⚠️ **{existente.nombre}** ya está inscrito bajo este número."
    
    db.add(Jugador(nombre=nombre, celular=celular, puntos=100))
    db.commit()
    
    total = db.query(Jugador).filter(Jugador.celular == celular).count()
    guardar_noticia(db, "¡NUEVO JUGADOR!", f"{nombre} se ha unido al circuito.", "anuncio")
    
    return f"✅ Inscrito: **{nombre}**. (Gestionas {total} perfiles)."

def obtener_estado_torneo(db: Session):
    """Devuelve la lista detallada de inscritos"""
    jugadores = db.query(Jugador).all()
    total = len(jugadores)
    
    if total == 0: return "Aún no hay inscritos."
    
    # Aquí está la corrección: LISTA DE NOMBRES
    nombres = "\n".join([f"• {j.nombre}" for j in jugadores])
    return (f"📊 *ESTADO DEL TORNEO*\n\n"
            f"👥 **Total Inscritos:** {total}\n"
            f"{nombres}\n\n"
            f"🔗 Ranking: https://torneo-pasto-ai.onrender.com")

def consultar_proximo_partido(db: Session, celular: str):
    mis = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis: return "No tienes inscritos."
    ids = [p.id for p in mis]
    parts = db.query(Partido).filter((Partido.jugador_1_id.in_(ids)) | (Partido.jugador_2_id.in_(ids)), Partido.estado == "pendiente").all()
    if not parts: return "📅 No tienes partidos programados."
    resp = "📅 **TUS PARTIDOS:**\n"
    for p in parts:
        mi = next((j for j in mis if j.id in [p.jugador_1_id, p.jugador_2_id]), None)
        riv = p.jugador_2_nombre if p.jugador_1_id == mi.id else p.jugador_1_nombre
        resp += f"\n👤 **{mi.nombre}** VS {riv}\n⏰ {p.hora} | 🏟️ {p.cancha}\n"
    return resp

def ejecutar_victoria_ia(db: Session, nombre_ganador: str, nombre_perdedor: str, puntos_ganados: int, puntos_perdidos: int, marcador: str, titulo_noticia: str, cuerpo_noticia: str):
    """Ejecuta la victoria calculada por la IA"""
    ganador = db.query(Jugador).filter(func.lower(Jugador.nombre) == nombre_ganador.lower()).first()
    perdedor = db.query(Jugador).filter(func.lower(Jugador.nombre) == nombre_perdedor.lower()).first()
    if not ganador or not perdedor: return "❌ Error: Jugadores no encontrados."

    ganador.puntos += puntos_ganados
    perdedor.puntos = max(0, perdedor.puntos - puntos_perdidos)
    ganador.victorias += 1
    perdedor.derrotas += 1
    
    partido = db.query(Partido).filter((Partido.estado == "pendiente"), (Partido.jugador_1_id.in_([ganador.id, perdedor.id])), (Partido.jugador_2_id.in_([ganador.id, perdedor.id]))).first()
    
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

    guardar_noticia(db, titulo_noticia, cuerpo_noticia, "partido")
    db.commit()
    return "OK"

# Wrapper para compatibilidad
def registrar_victoria(db, c, ng, nw, s1, s2): return "Usa la IA."