from database import SessionLocal
from logic import registrar_victoria

db = SessionLocal()

print("🎾 Simulando que Daniel Profe acaba de terminar un partido...")

# Simulamos que Daniel ganó 3 sets a 1
mensaje = registrar_victoria(db, nombre_ganador="Daniel Profe", sets_ganador=3, sets_perdedor=1)

print(mensaje)

db.close()