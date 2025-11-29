import os
import requests 
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import PlainTextResponse
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

# --- FUNCION PARA RESPONDER A WHATSAPP ---
def enviar_respuesta_whatsapp(numero: str, texto: str):
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID") 
    
    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }
    try:
        requests.post(url, headers=headers, json=data)
    except Exception as e:
        print(f"❌ Error enviando a Meta: {e}")

# RUTA 1: Dashboard
@app.get("/")
def ver_dashboard(request: Request, db: Session = Depends(get_db)):
    jugadores = db.query(models.Jugador).order_by(models.Jugador.ranking_inicial.desc()).all()
    partidos = db.query(models.Partido).all()
    return templates.TemplateResponse("ranking.html", {
        "request": request, 
        "jugadores": jugadores,
        "partidos": partidos
    })

# RUTA 2: Verificación (GET)
@app.get("/webhook")
def verificar_token(request: Request):
    verify_token = os.getenv("VERIFY_TOKEN", "pasto_ai_secreto")
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == verify_token:
        return PlainTextResponse(content=params.get("hub.challenge"), status_code=200)
    return {"status": "ok"}

# RUTA 3: Recibir Mensajes (POST)
@app.post("/webhook")
async def recibir_mensaje(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    try:
        value = data["entry"][0]["changes"][0]["value"]
        if "messages" in value:
            msg = value["messages"][0]
            if msg["type"] == "text":
                texto = msg["text"]["body"]
                numero = msg["from"]
                nombre = value["contacts"][0]["profile"]["name"]

                print(f"📩 MENSAJE: {texto} de {nombre}")

                # --- IA ---
                analisis = analizar_mensaje_ia(texto)
                
                if analisis["intencion"] == "reportar_victoria":
                    ganador = analisis["ganador"]
                    # Si la IA dice que ganó "Yo", usamos el nombre del perfil de WhatsApp
                    if ganador.lower() in ["yo", "mi", "mí"]:
                        ganador = nombre
                    
                    # Intentamos registrar
                    respuesta = registrar_victoria(
                        db, 
                        nombre_ganador=ganador, 
                        sets_ganador=analisis["sets_ganador"], 
                        sets_perdedor=analisis["sets_perdedor"]
                    )
                else:
                    respuesta = analisis.get("respuesta", "No entendí.")
                
                enviar_respuesta_whatsapp(numero, respuesta)
    except Exception as e:
        print(f"⚠️ Error: {e}")
    return {"status": "received"}

# --- RUTA MÁGICA: CREAR JUGADORES (SOLO ÚSALA UNA VEZ) ---
@app.get("/semilla")
def crear_datos_semilla(db: Session = Depends(get_db)):
    # 1. Crear a Daniel (Tú) - Asegúrate que el nombre sea EXACTO al de tu WhatsApp
    # En tu pantallazo vi que tu error dice "Daniel Martinez", así que usamos ese.
    daniel = models.Jugador(nombre="Daniel Martinez", ranking_inicial=1500, grupo="A")
    juan = models.Jugador(nombre="Juan", ranking_inicial=1400, grupo="A")
    
    db.add(daniel)
    db.add(juan)
    db.commit()
    db.refresh(daniel)
    db.refresh(juan)

    # 2. Crear partido pendiente
    partido = models.Partido(
        jugador_1_id=daniel.id, jugador_2_id=juan.id, 
        fase="Grupos", grupo="A", estado="pendiente", cancha="1"
    )
    db.add(partido)
    db.commit()
    
    return {"mensaje": "✅ ¡Daniel Martinez y Juan creados! Ya puedes reportar victoria."}