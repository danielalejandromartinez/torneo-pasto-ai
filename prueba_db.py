from database import SessionLocal, engine
import models

# Conectarnos a la base de datos
db = SessionLocal()

print("🛠️ Creando datos de prueba...")

# 1. Crear a Daniel (Tú)
daniel = models.Jugador(
    nombre="Daniel Martinez",  # Tiene que ser IGUAL a tu nombre de WhatsApp
    ranking_inicial=1500,
    grupo="A",
    puntos=0,
    sets_ganados=0,
    sets_perdidos=0,
    partidos_jugados=0
)

# 2. Crear a Juan (Tu rival)
juan = models.Jugador(
    nombre="Juan",
    ranking_inicial=1400,
    grupo="A",
    puntos=0,
    sets_ganados=0,
    sets_perdidos=0,
    partidos_jugados=0
)

# Guardamos los jugadores
db.add(daniel)
db.add(juan)
db.commit() # Confirmar cambios
print("✅ Jugadores Daniel y Juan creados.")

# 3. Crear el Partido Pendiente (Vital para que el bot funcione)
# Necesitamos saber sus IDs que se acaban de crear
db.refresh(daniel)
db.refresh(juan)

partido = models.Partido(
    jugador_1_id=daniel.id,
    jugador_2_id=juan.id,
    fase="Grupos",
    grupo="A",
    estado="pendiente", # <--- Esto es lo que busca el bot
    cancha="1"
)

db.add(partido)
db.commit()
print("✅ Partido Daniel vs Juan creado y pendiente.")

db.close()