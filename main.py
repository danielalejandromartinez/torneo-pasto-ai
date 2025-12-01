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
# Asegúrate de importar la nueva función consultar_estadisticas_torneo si la creaste en logic, 
# o usar obtener_estado_torneo que es la que definimos antes.
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
        texto_firmado = f"{texto}\n\n_Alejandro • Pasto.AI_"
        data = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": texto_firmado}}
        
        print(f"📤 INTENTANDO ENVIAR A {numero}...") # Debug
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print("✅ MENSAJE ENVIADO CON ÉXITO")
        else:
            print(f"❌ ERROR META: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error crítico WhatsApp: {e}")

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
                
                # Nombre seguro
                nombre_wa = "Jugador"
                if "contacts" in value:
                    nombre_wa = value["contacts"][0]["profile"]["name"]

                print(f"📩 RECIBIDO DE: {nombre_wa} ({numero}) MSG: {texto}")
                
                # --- VERIFICACIÓN DE ADMIN ---
                admin_real = os.getenv("ADMIN_PHONE")
                es_admin = str(numero) == str(admin_real)
                print(f"👮 ES ADMIN: {es_admin} (Esperaba: {admin_real}, Llegó: {numero})")

                # --- CEREBRO ---
                contexto = obtener_configuracion(db)
                analisis = analizar_mensaje_ia(texto, contexto)
                intencion = analisis.get("intencion")
                print(f"🧠 INTENCIÓN: {intencion}")
                
                respuesta = ""

                # --- ACCIONES ---
                if intencion == "admin_configurar":
                    if es_admin:
                        respuesta = actualizar_configuracion(db, analisis.get("clave"), analisis.get("valor"))
                    else:
                        respuesta = "❌ No tienes permisos de administrador."

                elif intencion == "admin_difusion":
                    if es_admin:
                        respuesta = enviar_difusion_masiva(db, analisis.get("mensaje"))
                    else:
                        respuesta = "❌ No tienes permisos."

                elif intencion == "inscripcion":
                    nombre_real = analisis.get("nombre", nombre_wa)
                    if not nombre_real or nombre_real == "Jugador": nombre_real = nombre_wa
                    respuesta = inscribir_jugador(db, nombre_real, numero)
                
                elif intencion == "consultar_estado":
                    # Aquí responde con la info de la base de datos (Contexto)
                    if not contexto or "Aún no hay reglas" in contexto:
                        respuesta = obtener_estado_torneo(db) # Info genérica si no hay reglas
                    else:
                        respuesta = f"ℹ️ **Información Oficial:**\n\n{contexto}"

                elif intencion == "consulta_inscritos":
                     # Usamos la función de estado que cuenta gente
                     respuesta = obtener_estado_torneo(db)

                elif intencion == "consultar_partido":
                    respuesta = consultar_proximo_partido(db, numero)
                
                elif intencion == "reportar_victoria":
                    respuesta = registrar_victoria(db, numero, analisis.get("sets_ganador", 3), analisis.get("sets_perdedor", 0))
                
                else:
                    respuesta = analisis.get("respuesta", "No entendí.")

                print(f"🤖 RESPUESTA A ENVIAR: {respuesta}")
                enviar_whatsapp(numero, respuesta)

    except Exception as e:
        print(f"🔥 ERROR SERVIDOR: {e}")
        traceback.print_exc()
        
    return {"status": "ok"}