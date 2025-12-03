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
    """Obtiene un valor de la configuración interna"""
    item = db.query(Configuracion).filter(Configuracion.key == key).first()
    return item.value if item else None

def set_config(db: Session, key: str, value: str):
    """Guarda un valor en la configuración interna"""
    item = db.query(Configuracion).filter(Configuracion.key == key).first()
    if not item:
        item = Configuracion(key=key, value=value)
        db.add(item)
    else:
        item.value = value
    db.commit()

def actualizar_configuracion(db: Session, clave: str, valor: str):
    """Función para que el admin guarde reglas manualmente"""
    set_config(db, clave, valor)
    return f"🫡 Listo jefe. He anotado que: **{clave}** es ahora **{valor}**."

def obtener_configuracion(db: Session):
    """Lee toda la libreta para darle contexto a la IA"""
    configs = db.query(Configuracion).all()
    texto_config = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    if not texto_config:
        return "Aún no hay reglas definidas por el administrador."
    return texto_config

def enviar_difusion_masiva(db: Session, mensaje: str):
    """Envía un mensaje a todos los celulares registrados (sin repetir)"""
    jugadores = db.query(Jugador.celular).distinct().all()
    if not jugadores:
        return "No hay jugadores inscritos para enviar el mensaje."
    
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    count = 0
    for j in jugadores:
        try:
            texto_final = f"📢 *ANUNCIO OFICIAL*\n\n{mensaje}\n\n_Alejandro • Pasto.AI_"
            data = {"messaging_product": "whatsapp", "to": j.celular, "type": "text", "text": {"body": texto_final}}
            requests.post(url, headers=headers, json=data)
            count += 1
        except:
            continue
            
    return f"✅ Mensaje enviado exitosamente a {count} números únicos."

# ==========================================
# 🧙‍♂️ WIZARD DE ORGANIZACIÓN (ESTA ES LA QUE FALTABA)
# ==========================================

def procesar_organizacion_torneo(db: Session, mensaje_usuario: str):
    """Máquina de estados para configurar el torneo paso a paso"""
    paso_actual = get_config(db, "wizard_paso")
    
    # BOTÓN DE ESCAPE
    if mensaje_usuario.lower() in ["cancelar", "salir", "abortar"]:
        set_config(db, "wizard_paso", "")
        return "🛑 Configuración cancelada. ¿En qué más te ayudo?"

    # INICIO DEL PROCESO
    if not paso_actual or mensaje_usuario.lower() in ["organizar torneo", "iniciar wizard", "configurar torneo"]:
        set_config(db, "wizard_paso", "canchas")
        return "👷‍♂️ ¡Listo Jefe! (Escribe 'Cancelar' para salir).\n\n1️⃣ **¿Cuántas canchas** tenemos disponibles? (Escribe solo el número, ej: 2)"

    # PASO 1: CANCHAS
    if paso_actual == "canchas":
        if not mensaje_usuario.isdigit():
            return "⚠️ Por favor escribe solo el número de canchas (Ej: 1, 2, 3)."
        set_config(db, "num_canchas", mensaje_usuario)
        set_config(db, "wizard_paso", "duracion")
        return f"✅ Entendido: {mensaje_usuario} canchas.\n\n2️⃣ **¿Cuántos minutos** dura cada partido? (Ej: 30, 45, 60)"

    # PASO 2: DURACIÓN
    if paso_actual == "duracion":
        if not mensaje_usuario.isdigit():
            return "⚠️ Escribe solo los minutos (Ej: 30)."
        set_config(db, "duracion_partido", mensaje_usuario)
        set_config(db, "wizard_paso", "hora")
        return f"✅ Ok, partidos de {mensaje_usuario} mins.\n\n3️⃣ **¿A qué hora** inicia el primer partido? (Formato 24h, Ej: 15:00)"

    # PASO 3: HORA
    if paso_actual == "hora":
        if ":" not in mensaje_usuario:
            return "⚠️ Usa el formato con dos puntos (Ej: 15:00)."
        set_config(db, "hora_inicio", mensaje_usuario)
        set_config(db, "wizard_paso", "confirmar")
        
        # Resumen para confirmar
        canchas = get_config(db, "num_canchas")
        duracion = get_config(db, "duracion_partido")
        return (f"📋 **RESUMEN DE CONFIGURACIÓN:**\n"
                f"- Canchas: {canchas}\n"
                f"- Duración: {duracion} min\n"
                f"- Inicio: {mensaje_usuario}\n\n"
                f"Si todo está bien, escribe: **GENERAR** para crear los partidos.")

    # PASO 4: GENERAR
    if paso_actual == "confirmar":
        if "generar" in mensaje_usuario.lower():
            set_config(db, "wizard_paso", "") # Reset del wizard
            return generar_partidos_automaticos(db) # Llamamos la función principal
        else:
            return "Escribe **GENERAR** para confirmar o 'Cancelar' para salir."

    return "No entendí. Escribe 'Cancelar' para reiniciar el asistente."

# ==========================================
# 🎾 LÓGICA DEL JUEGO (MULTI-PERFIL)
# ==========================================

def inscribir_jugador(db: Session, nombre: str, celular: str):
    # Verificar si el número ya existe CON ESE MISMO NOMBRE (insensible a mayúsculas)
    existente = db.query(Jugador).filter(
        Jugador.celular == celular, 
        func.lower(Jugador.nombre) == nombre.lower()
    ).first()
    
    if existente:
        return f"😅 ¡Oye! **{existente.nombre}** ya está en la lista bajo este número. No te preocupes, ya tiene su cupo asegurado."
    
    # Crear nuevo perfil familiar
    nuevo = Jugador(nombre=nombre, celular=celular, puntos=100, categoria="Novatos")
    db.add(nuevo)
    db.commit()
    
    total = db.query(Jugador).filter(Jugador.celular == celular).count()
    return (f"✅ **¡Inscripción Exitosa!**\n"
            f"👤 Jugador: **{nombre}**\n"
            f"📱 Cuenta: Vinculada a este WhatsApp.\n"
            f"Actualmente gestionas {total} perfiles desde este chat. ¡A ganar! 🎾")

def obtener_estado_torneo(db: Session):
    total = db.query(Jugador).count()
    info_admin = obtener_configuracion(db)
    return f"📊 *Estado del Circuito*\n👥 Inscritos: {total}\nℹ️ *Info Oficial:*\n{info_admin}"

def generar_partidos_automaticos(db: Session):
    jugadores = db.query(Jugador).all()
    if len(jugadores) < 2: return "❌ Faltan jugadores para iniciar."
    
    db.query(Partido).filter(Partido.estado == "pendiente").delete()
    random.shuffle(jugadores)
    
    # Leer Configuración de la Base de Datos
    try:
        num_canchas = int(get_config(db, "num_canchas") or 1)
        duracion = int(get_config(db, "duracion_partido") or 30)
        hora_str = get_config(db, "hora_inicio") or "12:00"
        
        hora_base = datetime.strptime(hora_str, "%H:%M")
        ahora = datetime.now()
        hora_base = hora_base.replace(year=ahora.year, month=ahora.month, day=ahora.day)
    except:
        return "⚠️ Error leyendo configuración. Usa el comando 'Organizar torneo' primero."

    creados = 0
    cancha_actual = 1
    slot_tiempo = 0
    
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
        
        # Rotación de canchas
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

def registrar_victoria(db: Session, celular: str, nombre_ganador_detectado: str, nombre_perfil_wa: str, s1: int, s2: int):
    # 1. Buscar mis perfiles
    mis_jugadores = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis_jugadores: return "No tienes perfiles inscritos."
    
    ids_jugadores = [p.id for p in mis_jugadores]
    
    # 2. Buscar partidos activos
    partidos = db.query(Partido).filter(
        (Partido.jugador_1_id.in_(ids_jugadores)) | (Partido.jugador_2_id.in_(ids_jugadores)),
        Partido.estado == "pendiente"
    ).all()
    
    if not partidos: return "No tienes partidos pendientes."
    
    partido_objetivo = None
    mi_jugador_ganador = None
    
    # INTELIGENCIA: DEFINIR QUIÉN ES EL 'CANDIDATO' A GANADOR
    candidato = nombre_ganador_detectado if nombre_ganador_detectado else nombre_perfil_wa
    
    # Caso A: Solo hay 1 partido activo en la familia
    if len(partidos) == 1:
        partido_objetivo = partidos[0]
        if partido_objetivo.jugador_1_id in ids_jugadores:
            mi_jugador_ganador = db.query(Jugador).get(partido_objetivo.jugador_1_id)
        else:
            mi_jugador_ganador = db.query(Jugador).get(partido_objetivo.jugador_2_id)
            
    # Caso B: Hay varios partidos
    else:
        for p in partidos:
            j1 = db.query(Jugador).get(p.jugador_1_id)
            j2 = db.query(Jugador).get(p.jugador_2_id)
            
            if candidato and candidato.lower() in j1.nombre.lower() and j1.id in ids_jugadores:
                partido_objetivo = p; mi_jugador_ganador = j1; break
            elif candidato and candidato.lower() in j2.nombre.lower() and j2.id in ids_jugadores:
                partido_objetivo = p; mi_jugador_ganador = j2; break
        
        if not partido_objetivo:
            return f"❌ No encontré un partido pendiente para **{candidato}** en tu cuenta."

    # Guardar resultado
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
    return f"🏆 **¡VICTORIA REGISTRADA!**\n\nGanador: **{mi_jugador_ganador.nombre}**\nMarcador: {s1}-{s2}\nRanking actualizado. 📈"