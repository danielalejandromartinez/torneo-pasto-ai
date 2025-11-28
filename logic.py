from sqlalchemy.orm import Session
from models import Jugador, Partido
import random

def iniciar_fase_grupos(db: Session):
    # 1. Traer a todos los jugadores ordenados por ranking (los mejores primero)
    jugadores = db.query(Jugador).order_by(Jugador.ranking_inicial.desc()).all()
    
    if len(jugadores) < 3:
        return "Error: Necesitamos al menos 3 jugadores para iniciar."

    # 2. Definir cuántos grupos (Idealmente de 3 o 4 personas)
    num_jugadores = len(jugadores)
    tamano_grupo_ideal = 4
    num_grupos = (num_jugadores // tamano_grupo_ideal) + (1 if num_jugadores % tamano_grupo_ideal != 0 else 0)
    
    # Si son muy pocos, hacemos un solo grupo
    if num_grupos == 0: num_grupos = 1

    print(f"📊 Organizando {num_jugadores} jugadores en {num_grupos} grupos...")

    # 3. Asignación "Serpiente" (Para equilibrar niveles)
    grupos = {f"Grupo {chr(65+i)}": [] for i in range(num_grupos)} # Crea Grupo A, B, C...
    nombres_grupos = list(grupos.keys())

    for i, jugador in enumerate(jugadores):
        # Esta matemática distribuye: 1->A, 2->B, 3->A, 4->B...
        indice_grupo = i % num_grupos
        nombre_grupo = nombres_grupos[indice_grupo]
        
        # Guardar en base de datos a qué grupo pertenece
        jugador.grupo = nombre_grupo
        grupos[nombre_grupo].append(jugador)
        db.add(jugador)

    # 4. Generar los Partidos (Round Robin - Todos contra Todos)
    total_partidos = 0
    for nombre_grupo, lista_jugadores in grupos.items():
        # Algoritmo de combinaciones: Jugador 1 vs 2, 1 vs 3, 2 vs 3...
        for i in range(len(lista_jugadores)):
            for j in range(i + 1, len(lista_jugadores)):
                p1 = lista_jugadores[i]
                p2 = lista_jugadores[j]
                
                nuevo_partido = Partido(
                    jugador_1_id=p1.id,
                    jugador_2_id=p2.id,
                    fase="Grupos",
                    grupo=nombre_grupo,
                    estado="pendiente",
                    cancha="Por definir"
                )
                db.add(nuevo_partido)
                total_partidos += 1

    db.commit()
    return f"✅ ¡Éxito! Se crearon {total_partidos} partidos en {num_grupos} grupos."

def registrar_victoria(db: Session, nombre_ganador: str, sets_ganador: int, sets_perdedor: int):
    # 1. Buscar al jugador que dice que ganó (insensible a mayúsculas)
    ganador = db.query(Jugador).filter(Jugador.nombre.ilike(f"%{nombre_ganador}%")).first()
    
    if not ganador:
        return f"❌ No encontré al jugador {nombre_ganador}."

    # 2. Buscar su partido pendiente
    # Buscamos un partido donde él esté jugando (como jugador 1 o 2) y que esté "pendiente"
    partido = db.query(Partido).filter(
        (Partido.jugador_1_id == ganador.id) | (Partido.jugador_2_id == ganador.id),
        Partido.estado == "pendiente"
    ).first()

    if not partido:
        return f"⚠️ {ganador.nombre} no tiene partidos pendientes programados."

    # 3. Identificar al rival
    if partido.jugador_1_id == ganador.id:
        perdedor = partido.jugador_2
    else:
        perdedor = partido.jugador_1

    # 4. Actualizar el Partido
    partido.ganador_id = ganador.id
    partido.marcador_sets = f"{sets_ganador}-{sets_perdedor}"
    partido.estado = "finalizado"

    # 5. Dar los puntos (Regla: 3 al ganador, 1 al perdedor)
    ganador.puntos += 3
    ganador.sets_ganados += sets_ganador
    ganador.sets_perdidos += sets_perdedor
    ganador.partidos_jugados += 1

    perdedor.puntos += 1
    perdedor.sets_ganados += sets_perdedor
    perdedor.sets_perdidos += sets_ganador
    perdedor.partidos_jugados += 1

    db.commit()
    
    return f"✅ Partido registrado: {ganador.nombre} ganó {sets_ganador}-{sets_perdedor} contra {perdedor.nombre}. Ranking actualizado."