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
    inscribir_jugador, generar_partidos_automaticos, consultar_proximo_partido, 
    registrar_victoria, obtener_estado_torneo, obtener_configuracion, 
    actualizar_configuracion, enviar_difusion_masiva
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
        
        # --- FIRMA PROFESIONAL ---
        # Solo la ponemos si no es una respuesta muy cortita (para que se vea natural)
        if len(texto) > 20:
            texto_final = f"{texto}\n\n━━━━━━━━━━━━━━━━\n🚀 *Desarrollado por Pasto.AI*\nSoluciones de IA para Profesionales"
        else:
            texto_final = texto # Si responde "Dale", no ponemos firma para que sea muy humano
            
        data = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": texto_final}}
        print(f"📤 Enviando a {numero}...") 
        requests.post(url, headers=headers, json=data)
    except Exception as e:
        print(f"❌ Error WhatsApp: {e}")

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
                
                # Contexto y Cerebro
                contexto = obtener_configuracion(db)
                analisis = analizar_mensaje_ia(texto, contexto)
                accion = analisis.get("accion")
                print(f"🧠 ACCIÓN: {accion}")
                
                respuesta = ""
                es_admin = str(numero) == str(os.getenv("ADMIN_PHONE"))

                # --- RESPUESTAS ---
                if accion == "conversacion":
                    respuesta = analisis.get("respuesta_ia")

                elif accion == "inscripcion":
                    datos = analisis.get("datos", {})
                    nombre_real = datos.get("nombre", nombre_wa)
                    if nombre_real == "Jugador": nombre_real = nombre_wa
                    respuesta = inscribir_jugador(db, nombre_real, numero)
                
                elif accion == "consultar_inscritos":
                    respuesta = obtener_estado_torneo(db)

                elif accion == "consultar_partido":
                    respuesta = consultar_proximo_partido(db, numero)
                
                elif accion == "reportar_victoria":
                    datos = analisis.get("datos", {})
                    respuesta = registrar_victoria(db, numero, datos.get("sets_ganador", 3), datos.get("sets_perdedor", 0))

                elif accion == "admin_configurar":
                    if es_admin:
                        datos = analisis.get("datos", {})
                        respuesta = actualizar_configuracion(db, datos.get("clave"), datos.get("valor"))
                    else:
                        respuesta = "❌ Solo el administrador puede configurar esto."

                elif accion == "admin_difusion":
                    if es_admin:
                        datos = analisis.get("datos", {})
                        respuesta = enviar_difusion_masiva(db, datos.get("mensaje"))
                    else:
                        respuesta = "❌ Acceso denegado."

                elif accion == "admin_iniciar":
                    if es_admin:
                        respuesta = generar_partidos_automaticos(db)
                    else:
                        respuesta = "❌ Esperando orden del administrador."

                enviar_whatsapp(numero, respuesta)

    except Exception as e:
        print(f"🔥 Error Servidor: {e}")
        traceback.print_exc()
        
    return {"status": "ok"}