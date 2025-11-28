from database import SessionLocal
from models import Jugador

# Abrimos la conexión a la base de datos
db = SessionLocal()

print("🌱 Sembrando jugadores en la base de datos...")

# Verificamos si ya existen para no duplicarlos
if db.query(Jugador).count() == 0:
    lista_jugadores = [
        Jugador(nombre="Daniel Profe", telefono="573001234567", ranking_inicial=1000),
        Jugador(nombre="Carlos Crack", telefono="573111111111", ranking_inicial=950),
        Jugador(nombre="Ana Principiante", telefono="573222222222", ranking_inicial=500),
        Jugador(nombre="Pedro Potencia", telefono="573333333333", ranking_inicial=800),
        Jugador(nombre="Luisa Volea", telefono="573444444444", ranking_inicial=750)
    ]

    db.add_all(lista_jugadores)
    db.commit()
    print("✅ ¡5 Jugadores creados con éxito!")
else:
    print("⚠️ Ya había jugadores, no se crearon nuevos.")

db.close()