import os
import requests 
import traceback 
from fastapi import FastAPI, Request, Depends
from fastapi.responses import PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from ai_agent import analizar_mensaje_ia
from logic import (
    inscribir_jugador, consultar_proximo_partido, registrar_victoria, 
    obtener_estado_torneo, obtener_contexto_completo,
    guardar_organizacion_ia # Nueva función potente
)

models.Base.metadata.create_all(bind=engine)
app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def enviar_whatsapp(numero, texto):
    try:
        token = os.getenv("WHATSAPP_TOKEN")
        phone_id = os.getenv("WHATSAPP_PHONE_ID")
        url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        if len(texto) > 40:
            texto_final = f"{texto}\n\n━━━━━━━━━━━━━━━━\n🚀 *Desarrollado por Pasto.AI*\nSoluciones de IA para Profesionales"
        else:
            texto_final = texto
            
        data = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": texto_final}}
        requests.post(url, headers=headers, json=data)
    except Exception as e:
        print(f"❌ Error WhatsApp: {e}")

@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    jugadores = db.query(models.Jugador).order_by(models.Jugador.puntos.desc()).all()
    return templates.TemplateResponse("ranking.html", {"request": request, "jugadores": jugadores})

@app.get("/programacion")
def ver_programacion(request: Request, db: Session = Depends(get_db)):
    partidos = db.query(models.Partido).order_by(models.Partido.hora.asc()).all()
    return templates.TemplateResponse("partidos.html", {"request": request, "partidos": partidos})

@app.get("/webhook")
def verificar(request: Request):
    if request.query_params.get("hub.verify_token") == os.getenv("VERIFY_TOKEN"):
        return PlainTextResponse(content=request.query_params.get("hub.challenge"), status_code=200)
    return {"status": "error"}

@app.post("/webhook")
async def recibir(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        
        if "messages" in value:
            msg = value["messages"][0]
            if msg["type"] == "text":
                texto = msg["text"]["body"]
                numero = msg["from"]
                
                nombre_wa = "Jugador"
                if "contacts" in value:
                    nombre_wa = value["contacts"][0]["profile"]["name"]

                print(f"📩 {nombre_wa}: {texto}")
                
                # 1. CONTEXTO COMPLETO (La IA ve todo)
                contexto = obtener_contexto_completo(db)
                
                # 2. CEREBRO AUTÓNOMO
                analisis = analizar_mensaje_ia(texto, contexto)
                accion = analisis.get("accion")
                datos = analisis.get("datos", {})
                
                print(f"🧠 ACCIÓN IA: {accion}")
                
                respuesta = ""
                es_admin = str(numero) == str(os.getenv("ADMIN_PHONE"))

                # --- EJECUCIÓN ---
                if accion == "conversacion":
                    respuesta = analisis.get("respuesta_ia", "Hola")

                elif accion == "inscripcion":
                    nombre_real = datos.get("nombre", nombre_wa)
                    if not nombre_real or nombre_real == "Jugador": nombre_real = nombre_wa
                    respuesta = inscribir_jugador(db, nombre_real, numero)
                
                elif accion == "guardar_organizacion_ia":
                    if es_admin:
                        # La IA ya hizo el trabajo sucio, aquí solo guardamos
                        respuesta = guardar_organizacion_ia(db, datos.get("partidos", []))
                    else:
                        respuesta = "❌ Solo el admin puede organizar."

                elif accion == "consultar_inscritos":
                    respuesta = obtener_estado_torneo(db)

                elif accion == "consultar_partido":
                    respuesta = consultar_proximo_partido(db, numero)
                
                elif accion == "reportar_victoria":
                    nombre_ganador = datos.get("nombre_ganador", "")
                    respuesta = registrar_victoria(db, numero, nombre_ganador, nombre_wa, datos.get("sets_ganador", 3), datos.get("sets_perdedor", 0))

                if respuesta:
                    enviar_whatsapp(numero, respuesta)

    except Exception as e:
        print(f"🔥 Error: {e}")
        traceback.print_exc()
        
    return {"status": "ok"}