from sqlalchemy.orm import Session
from models import Jugador, Partido
import random
from datetime import datetime, timedelta

# --- 1. INSCRIPCIÓN ---
def inscribir_jugador(db: Session, nombre: str, celular: str):
    # Verificar si ya existe
    existente = db.query(Jugador).filter(Jugador.celular == celular).first()
    if existente:
        return f"Hola {existente.nombre}, ya estás inscrito con {existente.puntos} puntos. Espera a que inicie el torneo."
    
    nuevo = Jugador(nombre=nombre, celular=celular, puntos=100, categoria="Novatos")
    db.add(nuevo)
    db.commit()
    return f"✅ ¡Bienvenido al Circuito Pasto.AI, {nombre}!\nTu ranking inicial es: 100 Puntos.\nTe avisaré cuando salgan los cuadros."

# --- 2. GENERAR CUADROS (Botón Mágico) ---
def generar_partidos_automaticos(db: Session):
    jugadores = db.query(Jugador).all()
    if len(jugadores) < 2:
        return "❌ Necesito al menos 2 jugadores inscritos."

    # Limpiar partidos viejos pendientes
    db.query(Partido).filter(Partido.estado == "pendiente").delete()
    
    # Mezclar y emparejar
    random.shuffle(jugadores)
    partidos_creados = []
    
    # Lógica simple: 1 vs 2, 3 vs 4...
    for i in range(0, len(jugadores) - 1, 2):
        p1 = jugadores[i]
        p2 = jugadores[i+1]
        
        # Asignar Horarios (Simulado para la prueba: Cada 30 mins)
        hora_base = datetime.now() + timedelta(minutes=10) # Empieza en 10 mins
        hora_partido = hora_base + timedelta(minutes=30 * (i//2))
        hora_str = hora_partido.strftime("%I:%M %p")
        cancha = "1" if (i//2) % 2 == 0 else "2" # Alternar canchas

        nuevo = Partido(
            jugador_1_id=p1.id, jugador_1_nombre=p1.nombre,
            jugador_2_id=p2.id, jugador_2_nombre=p2.nombre,
            cancha=cancha, hora=hora_str, estado="pendiente"
        )
        db.add(nuevo)
        partidos_creados.append(nuevo)
    
    db.commit()
    return f"✅ ¡Torneo Iniciado! Se crearon {len(partidos_creados)} partidos. Los jugadores pueden preguntar '¿A qué hora juego?'"

# --- 3. CONSULTAR MI PARTIDO ---
def consultar_proximo_partido(db: Session, celular: str):
    jugador = db.query(Jugador).filter(Jugador.celular == celular).first()
    if not jugador:
        return "No estás inscrito. Di 'Quiero inscribirme' para empezar."
    
    partido = db.query(Partido).filter(
        (Partido.jugador_1_id == jugador.id) | (Partido.jugador_2_id == jugador.id),
        Partido.estado == "pendiente"
    ).first()
    
    if not partido:
        return f"{jugador.nombre}, no tienes partidos programados por ahora. ¡Revisa el ranking!"
    
    rival = partido.jugador_2_nombre if partido.jugador_1_id == jugador.id else partido.jugador_1_nombre
    return f"📅 *TU PRÓXIMO PARTIDO*\n🆚 Rival: {rival}\n⏰ Hora: {partido.hora}\n🏟️ Cancha: {partido.cancha}\n\nCuando terminen, reporta el resultado diciendo: 'Gané 3-0'."

# --- 4. REGISTRAR RESULTADO (Sistema Puntos Simplificado) ---
def registrar_victoria(db: Session, celular_ganador: str, sets_ganador: int, sets_perdedor: int):
    ganador = db.query(Jugador).filter(Jugador.celular == celular_ganador).first()
    if not ganador: return "No estás inscrito."

    partido = db.query(Partido).filter(
        ((Partido.jugador_1_id == ganador.id) | (Partido.jugador_2_id == ganador.id)) & (Partido.estado == "pendiente")
    ).first()

    if not partido: return "No tienes partido pendiente para reportar."

    # Identificar Perdedor
    id_perdedor = partido.jugador_2_id if partido.jugador_1_id == ganador.id else partido.jugador_1_id
    perdedor = db.query(Jugador).filter(Jugador.id == id_perdedor).first()

    # --- MATEMÁTICA DE PUNTOS (SISTEMA DE ROBO) ---
    puntos_en_juego = 10 # Base
    
    # Si el débil le gana al fuerte (Batacazo), roba más
    if ganador.puntos < perdedor.puntos:
        puntos_en_juego = 20 # Premio doble
    
    # Transferencia
    ganador.puntos += puntos_en_juego
    perdedor.puntos = max(0, perdedor.puntos - puntos_en_juego) # No bajar de 0
    
    # Guardar stats
    ganador.victorias += 1
    perdedor.derrotas += 1
    partido.estado = "finalizado"
    partido.ganador_id = ganador.id
    partido.marcador = f"{sets_ganador}-{sets_perdedor}"
    
    db.commit()
    
    return (f"✅ *Resultado Confirmado*\n"
            f"🏆 {ganador.nombre} (+{puntos_en_juego} pts) -> {ganador.puntos}\n"
            f"📉 {perdedor.nombre} (-{puntos_en_juego} pts) -> {perdedor.puntos}\n"
            f"🔗 Mira el ranking: https://torneo-pasto-ai.onrender.com")