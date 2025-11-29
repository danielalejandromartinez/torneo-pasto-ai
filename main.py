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
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        # Si sale esto en los logs, es que funcionó:
        print(f"✅ MENSAJE ENVIADO A META EXITOSAMENTE: {numero}")
    except Exception as e:
        print(f"❌ ERROR ENVIANDO A META: {e}")
        print(f"Detalle: {response.text if 'response' in locals() else 'No response'}")


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
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == verify_token:
            return PlainTextResponse(content=challenge, status_code=200)
        else:
            raise HTTPException(status_code=403, detail="Token incorrecto")
    return {"status": "ok"}

# RUTA 3: Recibir Mensajes (POST)
@app.post("/webhook")
async def recibir_mensaje(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        if "messages" in value:
            mensaje_obj = value["messages"][0]
            
            if mensaje_obj["type"] != "text":
                return {"status": "ignored"}

            texto_recibido = mensaje_obj["text"]["body"]
            numero_usuario = mensaje_obj["from"] 
            nombre_usuario = value["contacts"][0]["profile"]["name"]

            print(f"📩 MENSAJE RECIBIDO: {texto_recibido} de {nombre_usuario}")

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
            
            # --- AQUÍ ESTÁ LA MAGIA: RESPONDER ---
            enviar_respuesta_whatsapp(numero_usuario, respuesta_final)

    except Exception as e:
        print(f"⚠️ Error procesando mensaje: {e}")

    return {"status": "received"}