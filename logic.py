from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Jugador, Partido, Configuracion, Noticia
import random
import os
import requests
from datetime import datetime, timedelta

# ==========================================
# 🧠 SISTEMA DE CLASIFICACIÓN (ZONAS)
# ==========================================
def obtener_zona(puntos):
    # Definimos las zonas según los puntos (puedes ajustar esto)
    # Para el MVP: Top 3 es Oro.
    if puntos >= 300: return "ORO"
    if puntos >= 200: return "PLATA"
    return "BRONCE"

def calcular_puntos_bounty(ganador_pts, perdedor_pts):
    zona_ganador = obtener_zona(ganador_pts)
    zona_perdedor = obtener_zona(perdedor_pts)
    
    # REGLA: Ganas el valor de la cabeza del rival
    puntos_base = 15 # Valor Bronce
    if zona_perdedor == "PLATA": puntos_base = 30
    if zona_perdedor == "ORO": puntos_base = 50
    
    return puntos_base

# ==========================================
# 📰 SALA DE PRENSA
# ==========================================
def guardar_noticia(db: Session, titulo: str, cuerpo: str, tipo: str="general"):
    try:
        db.add(Noticia(titulo=titulo, cuerpo=cuerpo, tipo=tipo))
        db.commit()
    except: pass

def obtener_contexto_completo(db: Session):
    jugadores = db.query(Jugador).order_by(Jugador.puntos.desc()).all()
    lista = ""
    for i, j in enumerate(jugadores):
        zona = obtener_zona(j.puntos)
        lista += f"#{i+1} {j.nombre} ({j.puntos}pts - {zona})\n"
    
    if not lista: lista = "Sin inscritos."
    
    # Partidos pendientes
    pendientes = db.query(Partido).filter(Partido.estado == "pendiente").all()
    lista_p = "\n".join([f"- {p.jugador_1_nombre} vs {p.jugador_2_nombre} ({p.hora})" for p in pendientes])
    
    return f"RANKING:\n{lista}\n\nPARTIDOS PENDIENTES:\n{lista_p}"

# ==========================================
# ⚖️ SISTEMA VAR (ARBITRAJE)
# ==========================================

def iniciar_proceso_resultado(db: Session, celular_reportante: str, nombre_ganador: str, nombre_perdedor: str, marcador: str):
    """
    1. Busca el partido.
    2. Lo pone en 'esperando_confirmacion'.
    3. Retorna los datos para que Main le escriba al rival.
    """
    # Buscar jugadores
    ganador = db.query(Jugador).filter(func.lower(Jugador.nombre).contains(nombre_ganador.lower())).first()
    perdedor = db.query(Jugador).filter(func.lower(Jugador.nombre).contains(nombre_perdedor.lower())).first()
    
    if not ganador or not perdedor: return {"status": "error", "msg": "No encontré esos nombres en la base de datos."}
    
    # Buscar el partido
    partido = db.query(Partido).filter(
        (Partido.estado == "pendiente"),
        (Partido.jugador_1_id.in_([ganador.id, perdedor.id])),
        (Partido.jugador_2_id.in_([ganador.id, perdedor.id]))
    ).first()
    
    if not partido:
        # Si es un reto libre, lo creamos
        partido = Partido(
            jugador_1_id=ganador.id, jugador_1_nombre=ganador.nombre,
            jugador_2_id=perdedor.id, jugador_2_nombre=perdedor.nombre,
            cancha="Reto", hora=datetime.now().strftime("%I:%M %p"),
            estado="pendiente"
        )
        db.add(partido)
        db.commit()

    # Actualizar estado a confirmación
    partido.estado = "esperando_confirmacion"
    partido.temp_ganador_id = ganador.id
    partido.temp_reportado_por = celular_reportante
    partido.marcador = marcador # Guardamos temporalmente
    db.commit()

    # Identificar al rival (el que no reportó) para enviarle mensaje
    rival_id = perdedor.id if ganador.celular == celular_reportante else ganador.id
    rival = db.query(Jugador).get(rival_id)
    
    return {
        "status": "waiting",
        "msg_reportante": f"✅ Recibido. Le he escrito a **{rival.nombre}** para que confirme el resultado. Apenas responda, actualizo el ranking.",
        "rival_celular": rival.celular,
        "rival_nombre": rival.nombre,
        "msg_rival": f"🚨 **CONFIRMACIÓN DE RESULTADO**\n\nTu rival dice que el partido terminó:\n\n🏆 Ganador: **{ganador.nombre}**\n📊 Marcador: {marcador}\n\n¿Es correcto? Responde **SÍ** o **NO**."
    }

def validar_resultado(db: Session, celular_confirmante: str, decision: str):
    """
    Procesa el SÍ o NO del rival.
    """
    # Buscar si hay un partido esperando confirmación para este usuario
    jugadores_cel = db.query(Jugador).filter(Jugador.celular == celular_confirmante).all()
    ids = [j.id for j in jugadores_cel]
    
    partido = db.query(Partido).filter(
        Partido.estado == "esperando_confirmacion",
        (Partido.jugador_1_id.in_(ids) | Partido.jugador_2_id.in_(ids))
    ).first()
    
    if not partido: return "No tienes confirmaciones pendientes."
    
    if "si" in decision.lower() or "confirm" in decision.lower():
        # APLICAR RESULTADO (BOUNTY)
        ganador = db.query(Jugador).get(partido.temp_ganador_id)
        perdedor = db.query(Jugador).get(partido.jugador_2_id if partido.jugador_1_id == ganador.id else partido.jugador_1_id)
        
        puntos = calcular_puntos_bounty(ganador.puntos, perdedor.puntos)
        
        ganador.puntos += puntos
        perdedor.puntos = max(0, perdedor.puntos - 5) # Protección básica
        
        ganador.victorias += 1
        perdedor.derrotas += 1
        
        partido.estado = "finalizado"
        partido.ganador_id = ganador.id
        
        # Noticia
        titulo = "¡BATACAZO!" if puntos >= 30 else "VICTORIA"
        guardar_noticia(db, titulo, f"{ganador.nombre} vence a {perdedor.nombre}. Suma +{puntos} pts.", "partido")
        
        db.commit()
        return f"✅ **¡Confirmado!** El ranking se ha actualizado.\n🏆 {ganador.nombre} (+{puntos})\n📉 {perdedor.nombre} (-5)"
        
    else:
        # RECHAZADO
        partido.estado = "pendiente" # Vuelve a estado normal
        partido.temp_ganador_id = None
        db.commit()
        return "🛑 Has rechazado el resultado. El partido vuelve a estado pendiente. Pónganse de acuerdo o hablen con el Admin."

# ==========================================
# 📋 GESTIÓN Y ADMIN
# ==========================================

def inscribir_jugador(db: Session, nombre: str, celular: str):
    existente = db.query(Jugador).filter(Jugador.celular == celular, func.lower(Jugador.nombre) == nombre.lower()).first()
    if existente: return f"⚠️ {nombre} ya está inscrito."
    db.add(Jugador(nombre=nombre, celular=celular, puntos=100))
    db.commit()
    guardar_noticia(db, "NUEVO JUGADOR", f"{nombre} entra al ranking.", "anuncio")
    return f"✅ Inscrito: **{nombre}**."

def consultar_datos(db: Session, tipo: str, celular: str):
    if tipo == "ranking_general":
        top = db.query(Jugador).order_by(Jugador.puntos.desc()).limit(10).all()
        return "\n".join([f"#{i+1} {j.nombre} - {j.puntos} pts" for i,j in enumerate(top)])
    
    if tipo == "mis_partidos":
        mis = db.query(Jugador).filter(Jugador.celular == celular).all()
        ids = [p.id for p in mis]
        parts = db.query(Partido).filter((Partido.jugador_1_id.in_(ids)) | (Partido.jugador_2_id.in_(ids)), Partido.estado == "pendiente").all()
        if not parts: return "No tienes partidos."
        return "\n".join([f"{p.jugador_1_nombre} vs {p.jugador_2_nombre} ({p.hora})" for p in parts])
    
    return "Revisa la web: https://torneo-pasto-ai.onrender.com"

def gestionar_torneo_admin(db: Session, accion: str, datos: str):
    if accion == "generar_fixture":
        # Generador Round Robin Simple
        jugadores = db.query(Jugador).all()
        if len(jugadores) < 2: return "Faltan jugadores."
        db.query(Partido).filter(Partido.estado == "pendiente").delete()
        random.shuffle(jugadores)
        count = 0
        for i in range(len(jugadores)//2):
            db.add(Partido(
                jugador_1_id=jugadores[i*2].id, jugador_1_nombre=jugadores[i*2].nombre,
                jugador_2_id=jugadores[i*2+1].id, jugador_2_nombre=jugadores[i*2+1].nombre,
                hora="Por definir", cancha="1", estado="pendiente"
            ))
            count += 1
        db.commit()
        guardar_noticia(db, "PROGRAMACIÓN LISTA", f"{count} partidos generados.", "anuncio")
        return f"✅ Fixture generado: {count} partidos."
        
    return "Configuración guardada."