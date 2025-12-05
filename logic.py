from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Jugador, Partido, Configuracion, Noticia
import random
import os
import requests
from datetime import datetime, timedelta

# ==========================================
# 🧠 CONTEXTO (LOS OJOS DE ALEJANDRO)
# ==========================================

def obtener_contexto_completo(db: Session):
    """
    Esta función le entrega a la IA el estado actual del mundo.
    Alejandro leerá esto antes de decidir qué decir o hacer.
    """
    # 1. Jugadores y Ranking
    jugadores = db.query(Jugador).order_by(Jugador.puntos.desc()).all()
    lista_jugadores = []
    for j in jugadores:
        lista_jugadores.append(f"- {j.nombre} (ID: {j.id} | Puntos: {j.puntos} | Celular: {j.celular})")
    txt_jugadores = "\n".join(lista_jugadores) if lista_jugadores else "No hay inscritos aún."

    # 2. Partidos Pendientes
    partidos = db.query(Partido).filter(Partido.estado == "pendiente").all()
    lista_partidos = []
    for p in partidos:
        lista_partidos.append(f"- {p.jugador_1_nombre} vs {p.jugador_2_nombre} (Hora: {p.hora}, Cancha: {p.cancha})")
    txt_partidos = "\n".join(lista_partidos) if lista_partidos else "No hay partidos programados."

    # 3. Configuración
    configs = db.query(Configuracion).all()
    txt_config = "\n".join([f"- {c.key}: {c.value}" for c in configs])

    return f"""
    === ESTADO ACTUAL DEL TORNEO ===
    
    👥 JUGADORES (RANKING):
    {txt_jugadores}
    
    📅 PARTIDOS PENDIENTES (PROGRAMACIÓN):
    {txt_partidos}
    
    ⚙️ CONFIGURACIÓN TÉCNICA:
    {txt_config}
    ================================
    """

# ==========================================
# 🛠️ HERRAMIENTAS DE ACCIÓN
# ==========================================

def guardar_noticia(db: Session, titulo: str, cuerpo: str, tipo: str="general"):
    try:
        db.add(Noticia(titulo=titulo, cuerpo=cuerpo, tipo=tipo))
        db.commit()
    except: pass

def inscribir_jugador_tool(db: Session, nombre: str, celular: str):
    # Verifica duplicados de nombre en el mismo celular
    existente = db.query(Jugador).filter(Jugador.celular == celular, func.lower(Jugador.nombre) == nombre.lower()).first()
    if existente: 
        return f"⚠️ {nombre} ya está inscrito. No es necesario repetir."
    
    db.add(Jugador(nombre=nombre, celular=celular, puntos=100)) # Inicia con 100 pts
    db.commit()
    
    guardar_noticia(db, "¡NUEVO FICHAJE!", f"{nombre} se une al circuito.", "anuncio")
    return "OK_INSCRITO"

def generar_fixture_tool(db: Session, lista_partidos: list):
    """Recibe la lista de partidos pensada por la IA y la guarda"""
    # Borramos pendientes anteriores para re-organizar
    db.query(Partido).filter(Partido.estado == "pendiente").delete()
    
    creados = 0
    for p in lista_partidos:
        # Buscamos los objetos jugador para tener sus IDs
        j1 = db.query(Jugador).filter(func.lower(Jugador.nombre) == p['j1_nombre'].lower()).first()
        j2 = db.query(Jugador).filter(func.lower(Jugador.nombre) == p['j2_nombre'].lower()).first()
        
        if j1 and j2:
            nuevo = Partido(
                jugador_1_id=j1.id, jugador_1_nombre=j1.nombre,
                jugador_2_id=j2.id, jugador_2_nombre=j2.nombre,
                cancha=str(p.get('cancha', '1')),
                hora=str(p.get('hora', 'Por definir')),
                estado="pendiente"
            )
            db.add(nuevo)
            creados += 1
            
    db.commit()
    guardar_noticia(db, "¡PROGRAMACIÓN LISTA!", f"Se han generado {creados} partidos nuevos.", "anuncio")
    return f"OK_FIXTURE_CREADO: {creados} partidos."

def reportar_victoria_tool(db: Session, nombre_ganador: str, nombre_perdedor: str, marcador: str):
    ganador = db.query(Jugador).filter(func.lower(Jugador.nombre) == nombre_ganador.lower()).first()
    perdedor = db.query(Jugador).filter(func.lower(Jugador.nombre) == nombre_perdedor.lower()).first()
    
    if not ganador or not perdedor: return "ERROR: Nombres no encontrados."

    # --- LÓGICA DE PUNTOS (SISTEMA BOUNTY) ---
    # Si el perdedor tenía más puntos que el ganador (Batacazo), el premio es mayor.
    if perdedor.puntos > ganador.puntos:
        puntos_juego = 50 # Premio gordo
    else:
        puntos_juego = 15 # Premio normal
    
    ganador.puntos += puntos_juego
    perdedor.puntos = max(0, perdedor.puntos - 5) # Protección: solo pierde 5
    
    ganador.victorias += 1
    perdedor.derrotas += 1
    
    # Cerrar el partido
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
        # Si fue un reto libre (sin programación previa), lo creamos y cerramos
        db.add(Partido(
            jugador_1_id=ganador.id, jugador_1_nombre=ganador.nombre,
            jugador_2_id=perdedor.id, jugador_2_nombre=perdedor.nombre,
            ganador_id=ganador.id, marcador=marcador, estado="finalizado",
            cancha="Reto", hora=datetime.now().strftime("%I:%M %p")
        ))

    # Noticia
    guardar_noticia(db, "¡RESULTADO!", f"{ganador.nombre} vence a {perdedor.nombre} ({marcador}).", "partido")
    db.commit()
    return f"OK_VICTORIA. Puntos sumados: {puntos_juego}."

def guardar_configuracion_tool(db: Session, clave: str, valor: str):
    item = db.query(Configuracion).filter(Configuracion.key == clave).first()
    if not item: db.add(Configuracion(key=clave, value=valor))
    else: item.value = valor
    db.commit()
    return "OK_CONFIG_GUARDADA"