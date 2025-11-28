import os
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from ai_agent import analizar_mensaje_ia
from logic import registrar_victoria

# Crear base de datos
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# RUTA 1: El Dashboard (TV)
@app.get("/")
def ver_dashboard(request: Request, db: Session = Depends(get_db)):
    jugadores = db.query(models.Jugador).order_by(models.Jugador.ranking_inicial.desc()).all()
    partidos = db.query(models.Partido).all()
    
    return templates.TemplateResponse("ranking.html", {
        "request": request, 
        "jugadores": jugadores,
        "partidos": partidos
    })

# RUTA 2: Verificación de WhatsApp (GET) - ¡NUEVO!
@app.get("/webhook")
def verificar_token(request: Request):
    """
    Meta envía una petición GET para verificar que somos nosotros.
    Debemos devolver el 'hub.challenge' si el token coincide.
    """
    verify_token = os.getenv("VERIFY_TOKEN", "pasto_ai_secreto")
    
    # Capturamos los parámetros de la URL
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == verify_token:
            print("✅ Webhook verificado exitosamente.")
            # Importante: Devolver el challenge como texto plano (int)
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Token incorrecto")
    
    return {"status": "ok"}

# RUTA 3: Recibir Mensajes (POST)
@app.post("/webhook")
async def recibir_mensaje(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    
    # Estructura REAL de WhatsApp (es compleja)
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        if "messages" in value:
            mensaje_obj = value["messages"][0]
            texto_recibido = mensaje_obj["text"]["body"]
            # El número viene como "57300..."
            numero_usuario = mensaje_obj["from"] 
            # Intentamos obtener el nombre del perfil, si no, usamos el número
            nombre_usuario = value["contacts"][0]["profile"]["name"]

            print(f"📩 WhatsApp Real: {texto_recibido} de {nombre_usuario}")

            # --- LÓGICA DE IA ---
            analisis = analizar_mensaje_ia(texto_recibido)
            respuesta_final = ""

            if analisis["intencion"] == "reportar_victoria":
                ganador = analisis["ganador"]
                if ganador.lower() in ["yo", "mi", "mí"]:
                    ganador = nombre_usuario
                
                resultado_db = registrar_victoria(
                    db, 
                    nombre_ganador=ganador, 
                    sets_ganador=analisis["sets_ganador"], 
                    sets_perdedor=analisis["sets_perdedor"]
                )
                respuesta_final = resultado_db
            else:
                respuesta_final = analisis.get("respuesta", "No entendí.")
            
            # AQUÍ FALTARÍA EL CÓDIGO PARA RESPONDERLE AL WHATSAPP DEL USUARIO
            # (Por ahora solo imprimimos en consola para no complicar el deploy)
            print(f"🤖 Respuesta del Bot: {respuesta_final}")

    except Exception as e:
        print(f"⚠️ Evento no manejado o error: {e}")

    return {"status": "received"}