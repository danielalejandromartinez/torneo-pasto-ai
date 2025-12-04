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
    inscribir_jugador, consultar_proximo_partido, 
    ejecutar_victoria_ia, obtener_estado_torneo, obtener_contexto_completo,
    guardar_organizacion_ia, guardar_configuracion_ia,
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
        token = os.getenv("WHATSAPP_TOKEN")
        phone_id = os.getenv("WHATSAPP_PHONE_ID")
        url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Firma profesional (solo si no es un mensaje muy corto)
        if texto and len(texto) > 50:
            texto_final = f"{texto}\n\n━━━━━━━━━━━━━━━━\n🚀 *Desarrollado por Pasto.AI*"
        else:
            texto_final = texto
            
        data = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": texto_final}}
        print(f"📤 Enviando a {numero}...")
        r = requests.post(url, headers=headers, json=data)
        if r.status_code != 200:
            print(f"❌ Error Meta: {r.text}")
    except Exception as e:
        print(f"❌ Error WhatsApp: {e}")

@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    jugadores = db.query(models.Jugador).order_by(models.Jugador.puntos.desc()).all()
    noticias = []
    try:
        noticias = db.query(models.Noticia).order_by(models.Noticia.fecha.desc()).limit(5).all()
    except: pass
    return templates.TemplateResponse("ranking.html", {"request": request, "jugadores": jugadores, "noticias": noticias})

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
                
                contexto = obtener_contexto_completo(db)
                
                # 1. CEREBRO IA ANALIZA
                analisis = analizar_mensaje_ia(texto, contexto)
                
                # Limpiamos la acción para evitar errores de espacios
                accion = str(analisis.get("accion", "conversacion")).strip().lower()
                datos = analisis.get("datos", {})
                respuesta_ia = analisis.get("respuesta_ia", "") # Lo que la IA quiere decir
                
                print(f"🧠 CEREBRO: {accion}")
                
                respuesta_final = ""
                es_admin = str(numero) == str(os.getenv("ADMIN_PHONE"))

                # --- 2. FILTRO DE ACCIONES TÉCNICAS (SOLO SI ES NECESARIO TOCAR LA BD) ---
                
                if accion == "inscripcion":
                    nombre_real = datos.get("nombre", nombre_wa)
                    if not nombre_real or nombre_real == "Jugador": nombre_real = nombre_wa
                    respuesta_final = inscribir_jugador(db, nombre_real, numero)
                
                elif accion == "reportar_victoria" or accion == "ejecutar_victoria_ia":
                    res_db = ejecutar_victoria_ia(
                        db, 
                        datos.get("nombre_ganador"), 
                        datos.get("nombre_perdedor"), 
                        datos.get("puntos_ganados"), 
                        datos.get("puntos_perdidos"), 
                        datos.get("marcador", "3-0"),
                        datos.get("titulo_noticia", "RESULTADO"),
                        datos.get("cuerpo_noticia", "Partido finalizado.")
                    )
                    respuesta_final = respuesta_ia if res_db == "OK" else f"⚠️ {res_db}"

                elif accion == "guardar_fixture_ia":
                    if es_admin:
                        respuesta_final = guardar_organizacion_ia(db, datos.get("partidos", []))
                    else: respuesta_final = "❌ Solo Admin."

                elif accion == "consultar_inscritos":
                    respuesta_final = obtener_estado_torneo(db)

                elif accion == "consultar_partido":
                    respuesta_final = consultar_proximo_partido(db, numero)

                elif accion == "admin_iniciar":
                    respuesta_final = respuesta_ia if respuesta_ia else "Comando recibido."

                # --- 3. RED DE SEGURIDAD (LA CLAVE) ---
                # Si no entró en ningún IF técnico, o si la acción era "conversacion", "saludo", "broma"...
                # ENTONCES RESPONDEMOS CON LO QUE DIJO LA IA (Chat natural).
                else:
                    respuesta_final = respuesta_ia

                # Si por alguna razón extrema la respuesta sigue vacía, mensaje de respaldo
                if not respuesta_final:
                    respuesta_final = "🤔 Estoy procesando..."

                enviar_whatsapp(numero, respuesta_final)

    except Exception as e:
        print(f"🔥 Error: {e}")
        traceback.print_exc()
        
    return {"status": "ok"}