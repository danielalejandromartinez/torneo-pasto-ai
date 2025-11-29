import os
import requests 
from fastapi import FastAPI, Request, Depends
from fastapi.responses import PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from ai_agent import analizar_mensaje_ia
from logic import inscribir_jugador, generar_partidos_automaticos, consultar_proximo_partido, registrar_victoria

models.Base.metadata.create_all(bind=engine)
app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def enviar_whatsapp(numero, texto):
    token = os.getenv("WHATSAPP_TOKEN")
    url = f"https://graph.facebook.com/v17.0/{os.getenv('WHATSAPP_PHONE_ID')}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    # Firma de Branding
    texto_firmado = f"{texto}\n\n_Alejandro • Powered by Pasto.AI_"
    data = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": texto_firmado}}
    requests.post(url, headers=headers, json=data)

@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    jugadores = db.query(models.Jugador).order_by(models.Jugador.puntos.desc()).all()
    partidos = db.query(models.Partido).all()
    return templates.TemplateResponse("ranking.html", {"request": request, "jugadores": jugadores, "partidos": partidos})

@app.get("/webhook")
def verificar(request: Request):
    if request.query_params.get("hub.verify_token") == os.getenv("VERIFY_TOKEN"):
        return PlainTextResponse(content=request.query_params.get("hub.challenge"), status_code=200)
    return {"status": "error"}

@app.post("/webhook")
async def recibir(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        if msg["type"] == "text":
            texto = msg["text"]["body"]
            numero = msg["from"]
            nombre_wa = data["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

            analisis = analizar_mensaje_ia(texto)
            intencion = analisis.get("intencion")

            respuesta = ""
            if intencion == "inscripcion":
                nombre_real = analisis.get("nombre", nombre_wa)
                if nombre_real == "Jugador": nombre_real = nombre_wa
                respuesta = inscribir_jugador(db, nombre_real, numero)
            
            elif intencion == "consultar_partido":
                respuesta = consultar_proximo_partido(db, numero)
            
            elif intencion == "reportar_victoria":
                respuesta = registrar_victoria(db, numero, analisis["sets_ganador"], analisis["sets_perdedor"])
            
            elif intencion == "info_general":
                respuesta = "🤖 Soy Alejandro, tu asistente de Squash.\nFui creado por **Pasto.AI** para organizar torneos automáticamente.\nSi eres médico o empresario, puedo ayudarte a agendar citas en tu negocio. Habla con Daniel Martínez."
            
            else:
                respuesta = analisis.get("respuesta", "No entendí.")

            enviar_whatsapp(numero, respuesta)
    except: pass
    return {"status": "ok"}

# --- RUTA PARA QUE TÚ INICIES EL TORNEO DESDE EL NAVEGADOR ---
@app.get("/iniciar_torneo")
def iniciar(db: Session = Depends(get_db)):
    return generar_partidos_automaticos(db)