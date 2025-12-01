from sqlalchemy.orm import Session
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
    # Convierte la lista en un texto legible
    texto_config = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    if not texto_config:
        return "Aún no hay reglas definidas por el administrador."
    return texto_config

# --- HERRAMIENTA DE DIFUSIÓN (MASIVO) ---
def enviar_difusion_masiva(db: Session, mensaje: str):
    jugadores = db.query(Jugador).all()
    if not jugadores:
        return "No hay jugadores inscritos para enviar el mensaje."
    
    count = 0
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    for j in jugadores:
        # Enviar uno por uno
        try:
            texto_final = f"📢 *ANUNCIO OFICIAL*\n\n{mensaje}\n\n_Alejandro • Pasto.AI_"
            data = {"messaging_product": "whatsapp", "to": j.celular, "type": "text", "text": {"body": texto_final}}
            requests.post(url, headers=headers, json=data)
            count += 1
        except:
            continue
            
    return f"✅ Mensaje enviado exitosamente a {count} jugadores."

# --- MANTENEMOS LAS FUNCIONES DEL JUEGO (Inscripción, Partidos, etc) ---
# (Copiadas tal cual para no romper nada)

def inscribir_jugador(db: Session, nombre: str, celular: str):
    existente = db.query(Jugador).filter(Jugador.celular == celular).first()
    if existente:
        return f"¡Hola parce! Ya estás inscrito. Tienes {existente.puntos} puntos. 👊"
    
    nuevo = Jugador(nombre=nombre, celular=celular, puntos=100, categoria="Novatos")
    db.add(nuevo)
    db.commit()
    return f"✅ ¡De una {nombre}! Quedaste inscrito.\nArrancas con 100 Puntos.\nTe aviso apenas salgan los cuadros. 🎾"

def obtener_estado_torneo(db: Session):
    total = db.query(Jugador).count()
    info_admin = obtener_configuracion(db) # Leemos lo que el jefe ordenó
    
    return (f"📊 *Estado del Circuito*\n"
            f"👥 Inscritos: {total}\n"
            f"ℹ️ *Info Oficial:*\n{info_admin}")

def generar_partidos_automaticos(db: Session):
    # (Misma lógica de antes)
    jugadores = db.query(Jugador).all()
    if len(jugadores) < 2: return "❌ Faltan jugadores."
    db.query(Partido).filter(Partido.estado == "pendiente").delete()
    random.shuffle(jugadores)
    creados = 0
    for i in range(0, len(jugadores) - 1, 2):
        p1, p2 = jugadores[i], jugadores[i+1]
        nuevo = Partido(jugador_1_id=p1.id, jugador_1_nombre=p1.nombre, jugador_2_id=p2.id, jugador_2_nombre=p2.nombre, cancha="1", hora="Por definir", estado="pendiente")
        db.add(nuevo)
        creados += 1
    db.commit()
    return f"✅ Cuadros generados ({creados} partidos). Los jugadores ya pueden consultar."

def consultar_proximo_partido(db: Session, celular: str):
    jugador = db.query(Jugador).filter(Jugador.celular == celular).first()
    if not jugador: return "No te veo en la lista, tigre. Escribe 'Quiero jugar' para inscribirte."
    partido = db.query(Partido).filter((Partido.jugador_1_id == jugador.id) | (Partido.jugador_2_id == jugador.id), Partido.estado == "pendiente").first()
    if not partido: return f"{jugador.nombre}, por ahora relax. No tienes partidos programados."
    rival = partido.jugador_2_nombre if partido.jugador_1_id == jugador.id else partido.jugador_1_nombre
    return f"📅 *PRÓXIMO RETO*\n🆚 VS: {rival}\n⏰ Hora: {partido.hora}\n🏟️ Cancha: {partido.cancha}"

def registrar_victoria(db: Session, celular_ganador: str, sets_ganador: int, sets_perdedor: int):
    ganador = db.query(Jugador).filter(Jugador.celular == celular_ganador).first()
    if not ganador: return "No estás inscrito."
    partido = db.query(Partido).filter(((Partido.jugador_1_id == ganador.id) | (Partido.jugador_2_id == ganador.id)) & (Partido.estado == "pendiente")).first()
    if not partido: return "No tienes partido pendiente."
    
    # Lógica de puntos
    id_perdedor = partido.jugador_2_id if partido.jugador_1_id == ganador.id else partido.jugador_1_id
    perdedor = db.query(Jugador).filter(Jugador.id == id_perdedor).first()
    
    ganador.puntos += 10
    perdedor.puntos = max(0, perdedor.puntos - 10)
    partido.estado = "finalizado"
    partido.ganador_id = ganador.id
    partido.marcador = f"{sets_ganador}-{sets_perdedor}"
    
    db.commit()
    return f"🔥 *¡Buena esa! Victoria registrada.*\n📈 {ganador.nombre}: {ganador.puntos} pts\n📉 {perdedor.nombre}: {perdedor.puntos} pts"