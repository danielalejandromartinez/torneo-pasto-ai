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
    actualizar_configuracion, enviar_difusion_masiva, procesar_organizacion_torneo
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
        print(f"🚀 INTENTANDO ENVIAR A {numero}...")
        token = os.getenv("WHATSAPP_TOKEN")
        phone_id = os.getenv("WHATSAPP_PHONE_ID")
        
        if not token or not phone_id:
            print("❌ ERROR: Faltan credenciales en Render.")
            return

        url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Firma profesional solo si el mensaje es largo
        if len(texto) > 40:
            texto_final = f"{texto}\n\n━━━━━━━━━━━━━━━━\n🚀 *Desarrollado por Pasto.AI*\nSoluciones de IA para Profesionales"
        else:
            texto_final = texto
            
        data = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": texto_final}}
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print("✅ MENSAJE ENTREGADO A META.")
        else:
            print(f"❌ ERROR META ({response.status_code}): {response.text}")
            
    except Exception as e:
        print(f"❌ Error crítico en función enviar_whatsapp: {e}")

@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    jugadores = db.query(models.Jugador).order_by(models.Jugador.puntos.desc()).all()
    partidos = db.query(models.Partido).all()
    return templates.TemplateResponse("ranking.html", {"request": request, "jugadores": jugadores, "partidos": partidos})

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

                print(f"📩 MENSAJE DE {nombre_wa}: {texto}")
                
                contexto = obtener_configuracion(db)
                analisis = analizar_mensaje_ia(texto, contexto)
                
                # --- AQUÍ ESTÁ EL ARREGLO CLAVE ---
                # Limpiamos la acción para evitar errores de espacios o mayúsculas
                accion_raw = analisis.get("accion", "conversacion")
                accion = str(accion_raw).strip().lower()
                
                datos = analisis.get("datos", {})
                print(f"🧠 CEREBRO PENSÓ: '{accion}'")
                
                respuesta = ""
                es_admin = str(numero) == str(os.getenv("ADMIN_PHONE"))

                # --- RUTAS DE RESPUESTA ---
                if accion == "conversacion":
                    respuesta = analisis.get("respuesta_ia", "Hola")

                elif accion == "inscripcion":
                    nombre_real = datos.get("nombre", nombre_wa)
                    if nombre_real == "Jugador" or not nombre_real: nombre_real = nombre_wa
                    respuesta = inscribir_jugador(db, nombre_real, numero)
                
                elif accion == "consultar_inscritos":
                    respuesta = obtener_estado_torneo(db)

                elif accion == "consultar_partido":
                    respuesta = consultar_proximo_partido(db, numero)
                
                elif accion == "reportar_victoria":
                    nombre_ganador = datos.get("nombre_ganador", "")
                    respuesta = registrar_victoria(db, numero, nombre_ganador, nombre_wa, datos.get("sets_ganador", 3), datos.get("sets_perdedor", 0))

                elif accion == "admin_wizard":
                    if es_admin:
                        respuesta = procesar_organizacion_torneo(db, datos.get("mensaje", ""))
                    else: respuesta = "❌ Solo Admin."

                elif accion == "admin_configurar":
                    if es_admin:
                        respuesta = actualizar_configuracion(db, datos.get("clave"), datos.get("valor"))
                    else: respuesta = "❌ Solo Admin."

                elif accion == "admin_difusion":
                    if es_admin:
                        respuesta = enviar_difusion_masiva(db, datos.get("mensaje"))
                    else: respuesta = "❌ Solo Admin."

                elif accion == "admin_iniciar":
                    if es_admin:
                        respuesta = procesar_organizacion_torneo(db, "organizar torneo")
                    else: respuesta = "❌ Solo Admin."
                
                else:
                    print(f"⚠️ ALERTA: Acción '{accion}' desconocida.")
                    respuesta = analisis.get("respuesta_ia", "No entendí tu solicitud.")

                # Enviar respuesta
                if respuesta:
                    enviar_whatsapp(numero, respuesta)
                else:
                    print("⚠️ ALERTA CRÍTICA: La variable 'respuesta' quedó vacía.")

    except Exception as e:
        print(f"🔥 Error Servidor: {e}")
        traceback.print_exc()
        
    return {"status": "ok"}