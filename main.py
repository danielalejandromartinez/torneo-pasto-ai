import os
import requests 
import traceback # Para ver los errores reales en los logs
from fastapi import FastAPI, Request, Depends
from fastapi.responses import PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from ai_agent import analizar_mensaje_ia
from logic import inscribir_jugador, generar_partidos_automaticos, consultar_proximo_partido, registrar_victoria

# Crear tablas en la base de datos si no existen
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Dependencia para obtener la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- FUNCION PARA ENVIAR MENSAJES A WHATSAPP ---
def enviar_whatsapp(numero, texto):
    try:
        token = os.getenv("WHATSAPP_TOKEN")
        phone_id = os.getenv("WHATSAPP_PHONE_ID")
        
        if not token or not phone_id:
            print("❌ Error: Faltan credenciales en .env (TOKEN o PHONE_ID)")
            return

        url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Agregamos la firma de marca
        texto_firmado = f"{texto}\n\n_Alejandro • Powered by Pasto.AI_"
        
        data = {
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "text",
            "text": {"body": texto_firmado}
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            print(f"❌ Error enviando a Meta ({response.status_code}): {response.text}")
        else:
            print(f"✅ Mensaje enviado a {numero}")

    except Exception as e:
        print(f"❌ Error crítico en enviar_whatsapp: {e}")

# RUTA 1: Dashboard (Ranking Web)
@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    # Ordenar jugadores por puntos de mayor a menor
    jugadores = db.query(models.Jugador).order_by(models.Jugador.puntos.desc()).all()
    partidos = db.query(models.Partido).all()
    return templates.TemplateResponse("ranking.html", {
        "request": request, 
        "jugadores": jugadores, 
        "partidos": partidos
    })

# RUTA 2: Verificación del Webhook (Para conectar con Meta)
@app.get("/webhook")
def verificar(request: Request):
    verify_token = os.getenv("VERIFY_TOKEN", "pasto_ai_secreto")
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == verify_token:
        return PlainTextResponse(content=challenge, status_code=200)
    return {"status": "error", "message": "Token incorrecto"}

# RUTA 3: Recibir Mensajes (El Cerebro)
@app.post("/webhook")
async def recibir(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        
        # Navegamos el JSON de WhatsApp con cuidado
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        
        if "messages" in value:
            msg = value["messages"][0]
            
            # Solo procesamos texto
            if msg["type"] == "text":
                texto = msg["text"]["body"]
                numero = msg["from"]
                
                # Extracción segura del nombre (A veces Meta no lo envía)
                nombre_wa = "Jugador"
                if "contacts" in value:
                    contacts = value.get("contacts", [])
                    if contacts:
                        nombre_wa = contacts[0].get("profile", {}).get("name", "Jugador")

                print(f"📩 MENSAJE RECIBIDO de {nombre_wa}: {texto}")

                # --- 1. INTELIGENCIA ARTIFICIAL ---
                analisis = analizar_mensaje_ia(texto)
                print(f"🧠 IA INTENCIÓN: {analisis}")
                
                intencion = analisis.get("intencion")
                respuesta = ""

                # --- 2. LÓGICA DE NEGOCIO ---
                
                if intencion == "inscripcion":
                    nombre_real = analisis.get("nombre", nombre_wa)
                    # Si la IA no encontró nombre, usamos el de WhatsApp
                    if not nombre_real or nombre_real == "Jugador":
                        nombre_real = nombre_wa
                    
                    respuesta = inscribir_jugador(db, nombre_real, numero)
                
                elif intencion == "consultar_partido":
                    respuesta = consultar_proximo_partido(db, numero)
                
                elif intencion == "reportar_victoria":
                    respuesta = registrar_victoria(
                        db, 
                        numero, 
                        analisis.get("sets_ganador", 3), 
                        analisis.get("sets_perdedor", 0)
                    )
                
                elif intencion == "info_general":
                    respuesta = "🤖 Hola, soy Alejandro, el asistente IA del Club.\nFui creado por **Pasto.AI** para organizar torneos automáticamente.\nSi eres profesional de la salud, puedo ayudarte a gestionar citas. Pregunta a Daniel Martínez."
                
                else:
                    respuesta = analisis.get("respuesta", "No te entendí bien. Intenta: 'Quiero inscribirme' o 'Gané 3-0'.")

                # --- 3. RESPONDER ---
                enviar_whatsapp(numero, respuesta)

    except Exception as e:
        # Si algo falla, esto nos lo mostrará en los logs de Render
        print(f"🔥 ERROR CRÍTICO EN EL SERVIDOR: {e}")
        traceback.print_exc()
        
    return {"status": "ok"}

# RUTA 4: Botón Mágico para Iniciar Torneo (Desde el navegador)
@app.get("/iniciar_torneo")
def iniciar(db: Session = Depends(get_db)):
    return generar_partidos_automaticos(db)