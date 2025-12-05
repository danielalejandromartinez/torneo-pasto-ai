import os
import requests 
import traceback 
from fastapi import FastAPI, Request, Depends
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from ai_agent import analizar_mensaje_ia
from logic import (
    inscribir_jugador, consultar_proximo_partido, 
    ejecutar_victoria_ia, obtener_estado_torneo, obtener_contexto_completo,
    guardar_organizacion_experta, guardar_configuracion_ia, # Nuevas funciones IA
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
        
        if len(texto) > 40: texto += "\n\n_Alejandro • Pasto.AI_"
        
        data = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": texto}}
        requests.post(url, headers=headers, json=data)
    except: pass

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    jugadores = db.query(models.Jugador).order_by(models.Jugador.puntos.desc()).all()
    noticias = []
    try: noticias = db.query(models.Noticia).order_by(models.Noticia.id.desc()).limit(5).all()
    except: pass
    return templates.TemplateResponse("ranking.html", {"request": request, "jugadores": jugadores, "noticias": noticias})

@app.get("/programacion", response_class=HTMLResponse)
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
                
                # 1. CONTEXTO TOTAL
                contexto = obtener_contexto_completo(db)
                
                # 2. CEREBRO EXPERTO
                analisis = analizar_mensaje_ia(texto, contexto)
                accion = str(analisis.get("accion", "conversacion")).strip().lower()
                datos = analisis.get("datos", {})
                respuesta_ia = analisis.get("respuesta_ia", "")
                
                print(f"🧠 ACCIÓN IA: {accion}")
                
                respuesta = ""
                es_admin = str(numero) == str(os.getenv("ADMIN_PHONE"))

                if accion == "conversacion":
                    respuesta = respuesta_ia

                elif accion == "inscripcion":
                    n = datos.get("nombre", nombre_wa)
                    if not n or n == "PERFIL_WHATSAPP": n = nombre_wa
                    respuesta = inscribir_jugador(db, n, numero)
                
                elif accion == "guardar_config":
                    if es_admin:
                        respuesta = guardar_configuracion_ia(db, datos.get("clave"), datos.get("valor"))
                    else: respuesta = "❌ Solo Admin."

                elif accion == "guardar_organizacion_experta":
                    if es_admin:
                        # Aquí la IA ya mandó el plan maestro. Logic solo lo guarda.
                        respuesta = guardar_organizacion_experta(db, datos.get("partidos", []))
                    else: respuesta = "❌ Solo Admin."

                elif accion == "consultar_inscritos":
                    respuesta = obtener_estado_torneo(db)

                elif accion == "consultar_partido":
                    respuesta = consultar_proximo_partido(db, numero)
                
                elif accion == "reportar_victoria" or accion == "ejecutar_victoria_ia":
                    nombre_ganador = datos.get("nombre_ganador", "")
                    # La IA ya calculó los puntos en el JSON, se los pasamos a Logic para guardar
                    res_db = ejecutar_victoria_ia(
                        db, 
                        nombre_ganador, 
                        datos.get("nombre_perdedor", ""), 
                        datos.get("puntos_ganados", 15), 
                        datos.get("puntos_perdidos", 5), 
                        datos.get("marcador", "3-0"),
                        datos.get("titulo_noticia", "RESULTADO"),
                        datos.get("cuerpo_noticia", "Finalizado.")
                    )
                    if res_db == "OK": respuesta = respuesta_ia
                    else: respuesta = f"⚠️ {res_db}"

                # ENVIAR
                if not respuesta: respuesta = respuesta_ia
                if not respuesta: respuesta = "Procesando solicitud..."
                
                enviar_whatsapp(numero, respuesta)

    except Exception as e:
        print(f"🔥 Error: {e}")
        traceback.print_exc()
        
    return {"status": "ok"}