from sqlalchemy.orm import Session
from models import Jugador, Partido, Configuracion
import random
import os
import requests
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
def actualizar_configuracion(db: Session, clave: str, valor: str):
    dato = db.query(Configuracion).filter(Configuracion.key == clave).first()
    if not dato:
        dato = Configuracion(key=clave, value=valor)
        db.add(dato)
    else:
        dato.value = valor
    db.commit()
    return f"🫡 Listo jefe. Configurado: **{clave}** = **{valor}**."

def obtener_configuracion(db: Session):
    configs = db.query(Configuracion).all()
    texto = "\n".join([f"- {c.key}: {c.value}" for c in configs])
    return texto if texto else "No hay reglas definidas aún."

def enviar_difusion_masiva(db: Session, mensaje: str):
    # Enviamos solo una vez por celular (para no spamear al papá 3 veces)
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

# --- LÓGICA FAMILIAR ---

def inscribir_jugador(db: Session, nombre: str, celular: str):
    # Verificar si YA existe ESTA persona en ESTE celular
    existente = db.query(Jugador).filter(Jugador.celular == celular, Jugador.nombre == nombre).first()
    
    if existente:
        return f"⚠️ **{nombre}** ya está inscrito bajo tu cuenta con {existente.puntos} puntos."
    
    # Crear nuevo perfil vinculado al celular
    nuevo = Jugador(nombre=nombre, celular=celular, puntos=100, categoria="Novatos")
    db.add(nuevo)
    db.commit()
    
    # Contamos cuántos perfiles tiene
    total = db.query(Jugador).filter(Jugador.celular == celular).count()
    
    return (f"✅ **¡Inscripción Exitosa!**\n"
            f"👤 Jugador: **{nombre}**\n"
            f"📱 Cuenta: Vinculada a tu WhatsApp.\n"
            f"Actualmente gestionas {total} perfiles desde este chat.")

def obtener_estado_torneo(db: Session):
    total = db.query(Jugador).count()
    info = obtener_configuracion(db)
    return f"📊 *Estado del Circuito*\n👥 Total Jugadores: {total}\nℹ️ *Info Oficial:*\n{info}"

def generar_partidos_automaticos(db: Session):
    jugadores = db.query(Jugador).all()
    if len(jugadores) < 2: return "❌ Faltan jugadores."
    
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
    return f"✅ ¡Torneo Iniciado! {creados} partidos generados."

def consultar_proximo_partido(db: Session, celular: str):
    # Buscar TODOS los perfiles de este celular
    mis_jugadores = db.query(Jugador).filter(Jugador.celular == celular).all()
    
    if not mis_jugadores:
        return "No tienes ningún perfil inscrito. Di 'Inscribir a [Nombre]'."
    
    ids_jugadores = [p.id for p in mis_jugadores]
    
    # Buscar partidos para CUALQUIERA de esos perfiles
    partidos = db.query(Partido).filter(
        (Partido.jugador_1_id.in_(ids_jugadores)) | (Partido.jugador_2_id.in_(ids_jugadores)),
        Partido.estado == "pendiente"
    ).all()
    
    if not partidos:
        nombres = ", ".join([p.nombre for p in mis_jugadores])
        return f"📅 No hay partidos programados para tus perfiles ({nombres}) por ahora."
    
    respuesta = "📅 **TUS PARTIDOS PENDIENTES:**\n"
    for p in partidos:
        # Encontrar cuál de mis perfiles juega en este partido
        mi_jugador = next((jug for jug in mis_jugadores if jug.id == p.jugador_1_id or jug.id == p.jugador_2_id), None)
        rival = p.jugador_2_nombre if p.jugador_1_id == mi_jugador.id else p.jugador_1_nombre
        
        respuesta += f"\n👤 **{mi_jugador.nombre}** VS {rival}\n⏰ {p.hora} | 🏟️ {p.cancha}\n"
        
    return respuesta

def registrar_victoria(db: Session, celular: str, nombre_ganador_detectado: str, sets_ganador: int, sets_perdedor: int):
    # Buscar mis perfiles
    mis_jugadores = db.query(Jugador).filter(Jugador.celular == celular).all()
    if not mis_jugadores: return "No tienes perfiles inscritos."
    
    ids_jugadores = [p.id for p in mis_jugadores]
    
    # Buscar partidos activos
    partidos = db.query(Partido).filter(
        (Partido.jugador_1_id.in_(ids_jugadores)) | (Partido.jugador_2_id.in_(ids_jugadores)),
        Partido.estado == "pendiente"
    ).all()
    
    if not partidos: return "No tienes partidos pendientes para reportar."
    
    partido_objetivo = None
    mi_jugador_ganador = None
    
    # INTELIGENCIA PARA SABER QUIÉN GANÓ
    
    # Caso A: Solo hay 1 partido en toda la familia. Asumimos que es ese.
    if len(partidos) == 1:
        partido_objetivo = partidos[0]
        # Verifico cuál de mis perfiles es el que ganó
        if partido_objetivo.jugador_1_id in ids_jugadores:
            mi_jugador_ganador = db.query(Jugador).get(partido_objetivo.jugador_1_id)
        else:
            mi_jugador_ganador = db.query(Jugador).get(partido_objetivo.jugador_2_id)
            
    # Caso B: Hay varios partidos. Necesitamos el nombre que dijo la IA.
    else:
        if not nombre_ganador_detectado:
            return f"⚠️ Tienes varios partidos activos. Por favor dime: **'Ganó [Nombre]'**."
        
        # Buscamos coincidencias
        for p in partidos:
            j1 = db.query(Jugador).get(p.jugador_1_id)
            j2 = db.query(Jugador).get(p.jugador_2_id)
            
            # Chequeamos si el nombre que dijo el usuario se parece a alguno de sus jugadores en partido
            if nombre_ganador_detectado.lower() in j1.nombre.lower() and j1.id in ids_jugadores:
                partido_objetivo = p
                mi_jugador_ganador = j1
                break
            elif nombre_ganador_detectado.lower() in j2.nombre.lower() and j2.id in ids_jugadores:
                partido_objetivo = p
                mi_jugador_ganador = j2
                break
        
        if not partido_objetivo:
            return f"❌ No encontré un partido para **{nombre_ganador_detectado}** en tu cuenta."

    # --- GUARDAR RESULTADO ---
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