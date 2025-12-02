from sqlalchemy.orm import Session
from sqlalchemy import func # Necesario para ignorar mayúsculas/minúsculas
from models import Jugador, Partido, Configuracion
import random
import os
import requests
from datetime import datetime, timedelta

# --- HERRAMIENTAS DEL JEFE (CONFIGURACIÓN) ---
def actualizar_configuracion(db: Session, clave: str, valor: str):
    """Guarda un dato en la libreta de Alejandro"""
    dato = db.query(Configuracion).filter(Configuracion.key == clave).first()
    if not dato:
        dato = Configuracion(key=clave, value=valor)
        db.add(dato)
    else:
        dato.value = valor
    db.commit()
    return f"🫡 Listo jefe. He anotado que: **{clave}** es ahora **{valor}**."

def obtener_configuracion(db: Session):
    """Lee toda la libreta para darle contexto a la IA"""
    configs = db.query(Configuracion).all()
    texto_config = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    if not texto_config:
        return "Aún no hay reglas definidas por el administrador."
    return texto_config

# --- HERRAMIENTA DE DIFUSIÓN (MASIVO) ---
def enviar_difusion_masiva(db: Session, mensaje: str):
    jugadores = db.query(Jugador.celular).distinct().all()
    if not jugadores:
        return "No hay jugadores inscritos para enviar el mensaje."
    
    count = 0
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    for j in jugadores:
        try:
            texto_final = f"📢 *ANUNCIO OFICIAL*\n\n{mensaje}\n\n_Alejandro • Pasto.AI_"
            data = {"messaging_product": "whatsapp", "to": j.celular, "type": "text", "text": {"body": texto_final}}
            requests.post(url, headers=headers, json=data)
            count += 1
        except:
            continue
            
    return f"✅ Mensaje enviado exitosamente a {count} jugadores."

# --- LÓGICA DEL JUEGO (MULTI-PERFIL) ---

def inscribir_jugador(db: Session, nombre: str, celular: str):
    # 1. Verificar si el número ya existe CON ESE MISMO NOMBRE (insensible a mayúsculas)
    # Ejemplo: Si ya existe "Maria", no deja crear "maria".
    existente = db.query(Jugador).filter(
        Jugador.celular == celular, 
        func.lower(Jugador.nombre) == nombre.lower()
    ).first()
    
    if existente:
        return f"😅 ¡Oye! **{existente.nombre}** ya está en la lista bajo este número. No te preocupes, ya tiene su cupo asegurado."
    
    # 2. Si no existe ese nombre en este celular, lo creamos (Nuevo perfil familiar)
    nuevo = Jugador(nombre=nombre, celular=celular, puntos=100, categoria="Novatos")
    db.add(nuevo)
    db.commit()
    
    # Contamos cuántos perfiles tiene este celular ahora
    total = db.query(Jugador).filter(Jugador.celular == celular).count()
    
    return (f"✅ **¡Inscripción Exitosa!**\n"
            f"👤 Jugador: **{nombre}**\n"
            f"📱 Cuenta: Vinculada a este WhatsApp.\n"
            f"Actualmente gestionas {total} perfiles desde este chat. ¡A ganar! 🎾")

def obtener_estado_torneo(db: Session):
    total = db.query(Jugador).count()
    info_admin = obtener_configuracion(db)
    
    return (f"📊 *Estado del Circuito*\n"
            f"👥 Inscritos: {total}\n"
            f"ℹ️ *Info Oficial:*\n{info_admin}")

def generar_partidos_automaticos(db: Session):
    jugadores = db.query(Jugador).all()
    if len(jugadores) < 2: return "❌ Faltan jugadores para iniciar."
    
    db.query(Partido).filter(Partido.estado == "pendiente").delete()
    random.shuffle(jugadores)
    creados = 0
    
    for i in range(0, len(jugadores) - 1, 2):
        p1, p2 = jugadores[i], jugadores[i+1]
        nuevo = Partido(
            jugador_1_id=p1.id, jugador_1_nombre=p1.nombre, 
            jugador_2_id=p2.id, jugador_2_nombre=p2.nombre, 
            cancha="1", hora="Por definir", estado="pendiente"
        )
        db.add(nuevo)
        creados += 1
    
    db.commit()
    return f"✅ Cuadros generados ({creados} partidos). Los jugadores ya pueden consultar."

def consultar_proximo_partido(db: Session, celular: str):
    mis_jugadores = db.query(Jugador).filter(Jugador.celular == celular).all()
    
    if not mis_jugadores:
        return "No te veo en la lista. Escribe 'Quiero inscribir a [Nombre]'."
    
    ids_jugadores = [p.id for p in mis_jugadores]
    
    partidos = db.query(Partido).filter(
        (Partido.jugador_1_id.in_(ids_jugadores)) | (Partido.jugador_2_id.in_(ids_jugadores)),
        Partido.estado == "pendiente"
    ).all()
    
    if not partidos:
        nombres = ", ".join([p.nombre for p in mis_jugadores])
        return f"📅 Tus perfiles ({nombres}) no tienen partidos programados por ahora."
    
    respuesta = "📅 **TUS PARTIDOS PENDIENTES:**\n"
    for p in partidos:
        mi_jugador = next((jug for jug in mis_jugadores if jug.id == p.jugador_1_id or jug.id == p.jugador_2_id), None)
        rival = p.jugador_2_nombre if p.jugador_1_id == mi_jugador.id else p.jugador_1_nombre
        respuesta += f"\n👤 **{mi_jugador.nombre}** VS {rival}\n⏰ {p.hora} | 🏟️ {p.cancha}\n"
        
    return respuesta

def registrar_victoria(db: Session, celular: str, nombre_ganador_detectado: str, sets_ganador: int, sets_perdedor: int):
    # Lógica inteligente para saber cuál de los familiares ganó
    mis_jugadores = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis_jugadores: return "No tienes perfiles inscritos."
    
    ids_jugadores = [p.id for p in mis_jugadores]
    
    partidos = db.query(Partido).filter(
        (Partido.jugador_1_id.in_(ids_jugadores)) | (Partido.jugador_2_id.in_(ids_jugadores)),
        Partido.estado == "pendiente"
    ).all()
    
    if not partidos: return "No tienes partidos pendientes para reportar."
    
    partido_objetivo = None
    mi_jugador_ganador = None
    
    # Caso A: Solo hay 1 partido activo en la familia
    if len(partidos) == 1:
        partido_objetivo = partidos[0]
        if partido_objetivo.jugador_1_id in ids_jugadores:
            mi_jugador_ganador = db.query(Jugador).get(partido_objetivo.jugador_1_id)
        else:
            mi_jugador_ganador = db.query(Jugador).get(partido_objetivo.jugador_2_id)
            
    # Caso B: Hay varios partidos (Ej: Juega papá e hijo al tiempo)
    else:
        if not nombre_ganador_detectado:
            return f"⚠️ Tienes varios partidos activos. Por favor dime explícitamente: **'Ganó [Nombre]'**."
        
        # Buscamos coincidencias de nombre
        for p in partidos:
            j1 = db.query(Jugador).get(p.jugador_1_id)
            j2 = db.query(Jugador).get(p.jugador_2_id)
            
            if nombre_ganador_detectado.lower() in j1.nombre.lower() and j1.id in ids_jugadores:
                partido_objetivo = p
                mi_jugador_ganador = j1
                break
            elif nombre_ganador_detectado.lower() in j2.nombre.lower() and j2.id in ids_jugadores:
                partido_objetivo = p
                mi_jugador_ganador = j2
                break
        
        if not partido_objetivo:
            return f"❌ No encontré un partido pendiente para **{nombre_ganador_detectado}** en tu cuenta."

    # Guardar resultado
    id_perdedor = partido_objetivo.jugador_2_id if partido_objetivo.jugador_1_id == mi_jugador_ganador.id else partido_objetivo.jugador_1_id
    perdedor = db.query(Jugador).get(id_perdedor)
    
    mi_jugador_ganador.puntos += 10
    perdedor.puntos = max(0, perdedor.puntos - 10)
    
    mi_jugador_ganador.victorias += 1
    perdedor.derrotas += 1
    
    partido_objetivo.estado = "finalizado"
    partido_objetivo.ganador_id = mi_jugador_ganador.id
    partido_objetivo.marcador = f"{sets_ganador}-{sets_perdedor}"
    
    db.commit()
    return f"🏆 **¡VICTORIA REGISTRADA!**\n\nGanador: **{mi_jugador_ganador.nombre}**\nMarcador: {sets_ganador}-{sets_perdedor}\nRanking actualizado. 📈"