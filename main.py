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
# Importamos todas las herramientas
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
        url = f"https://graph.facebook.com/v17.0/{os.getenv('WHATSAPP_PHONE_ID')}/messages"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        # Firma sutil
        texto_firmado = f"{texto}\n\n_Alejandro • Asistente Pasto.AI_"
        data = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": texto_firmado}}
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

                print(f"📩 MENSAJE de {nombre_wa} ({numero}): {texto}")
                
                # 1. LEER LA LIBRETA (Contexto)
                # Alejandro lee la base de datos para saber precios, fechas, etc.
                contexto = obtener_configuracion(db)

                # 2. CEREBRO IA
                analisis = analizar_mensaje_ia(texto, contexto)
                intencion = analisis.get("intencion")
                print(f"🧠 INTENCIÓN: {intencion}")
                
                respuesta = ""
                es_admin = numero == os.getenv("ADMIN_PHONE")

                # --- ACCIONES DE USUARIO ---
                if intencion == "inscripcion":
                    nombre_real = analisis.get("nombre", nombre_wa)
                    if not nombre_real or nombre_real == "Jugador": nombre_real = nombre_wa
                    respuesta = inscribir_jugador(db, nombre_real, numero)
                
                elif intencion == "consulta_general":
                    # Aquí la IA ya debería haber respondido usando el contexto en su cerebro, 
                    # pero si no, reforzamos con el estado del torneo.
                    respuesta = obtener_estado_torneo(db)

                elif intencion == "consultar_partido":
                    respuesta = consultar_proximo_partido(db, numero)
                
                elif intencion == "reportar_victoria":
                    respuesta = registrar_victoria(db, numero, analisis.get("sets_ganador", 3), analisis.get("sets_perdedor", 0))
                
                elif intencion == "info_ventas":
                    respuesta = "🤖 ¡Hola! Soy Alejandro, desarrollado por *Pasto.AI*.\nAyudo a empresas y consultorios a automatizar su atención por WhatsApp.\n¿Te gustaría tener un asistente como yo? Contacta a Daniel Martínez."

                # --- ACCIONES DE ADMINISTRADOR (SOLO TÚ) ---
                elif intencion == "admin_configurar":
                    if es_admin:
                        clave = analisis.get("clave")
                        valor = analisis.get("valor")
                        respuesta = actualizar_configuracion(db, clave, valor)
                    else:
                        respuesta = "❌ No tienes permisos de administrador."

                elif intencion == "admin_difusion":
                    if es_admin:
                        mensaje_masivo = analisis.get("mensaje")
                        respuesta = enviar_difusion_masiva(db, mensaje_masivo)
                    else:
                        respuesta = "❌ No tienes permisos."

                elif intencion == "admin_iniciar_torneo":
                    if es_admin:
                        respuesta = generar_partidos_automaticos(db)
                    else:
                        respuesta = "❌ Solo Daniel puede iniciar el torneo."

                else:
                    # Si es "otra", dejamos que la IA responda amablemente
                    respuesta = analisis.get("respuesta", "¡Hola! Estoy aquí para ayudarte con el torneo de Squash. 🎾")

                enviar_whatsapp(numero, respuesta)
    except Exception as e:
        print(f"🔥 Error: {e}")
        traceback.print_exc()
        
    return {"status": "ok"}