from database import SessionLocal
from logic import iniciar_fase_grupos
from models import Partido

db = SessionLocal()

# Limpiar partidos viejos si existieran (para reiniciar pruebas)
db.query(Partido).delete()
db.commit()

print("🏆 Iniciando motor de torneo Pasto.AI...")
resultado = iniciar_fase_grupos(db)
print(resultado)

db.close()
