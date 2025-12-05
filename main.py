import os
import requests 
import traceback 
import json
from fastapi import FastAPI, Request, Depends
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from ai_agent import pensar_respuesta_ia
from logic import (
    obtener_contexto_completo, inscribir_jugador, consultar_datos,
    iniciar_proceso_resultado, validar_resultado, gestionar_torneo_admin
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
        if len(texto) > 50: texto += "\n\n_Alejandro • Pasto.AI_"
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
                
                # Nombre
                nombre_wa = value.get("contacts", [{}])[0].get("profile", {}).get("name", "Usuario")
                print(f"📩 {nombre_wa}: {texto}")
                
                # --- CAPA 1: INTERCEPTAR SI O NO (Para validaciones rápidas) ---
                if texto.strip().upper() in ["SI", "SÍ", "NO", "CONFIRMO", "RECHAZO"]:
                    respuesta = validar_resultado(db, numero, texto)
                    enviar_whatsapp(numero, respuesta)
                    return {"status": "ok"}
                
                # --- CAPA 2: INTELIGENCIA ARTIFICIAL ---
                contexto = obtener_contexto_completo(db)
                decision = pensar_respuesta_ia(texto, contexto)
                
                respuesta = ""
                
                if decision["tipo"] == "mensaje":
                    respuesta = decision["contenido"]
                
                elif decision["tipo"] == "accion":
                    for tool in decision.get("tool_calls", []):
                        funcion = tool.function.name
                        args = json.loads(tool.function.arguments)
                        print(f"🔧 TOOL: {funcion}")
                        
                        if funcion == "inscribir_jugador":
                            nombre = args.get("nombre")
                            if nombre == "PERFIL_WHATSAPP": nombre = nombre_wa
                            respuesta = inscribir_jugador(db, nombre, numero)
                            
                        elif funcion == "consultar_datos":
                            respuesta = consultar_datos(db, args.get("tipo"), numero)
                            
                        elif funcion == "iniciar_proceso_resultado":
                            # AQUÍ OCURRE EL VAR
                            res_var = iniciar_proceso_resultado(
                                db, numero, 
                                args.get("ganador_supuesto"), 
                                args.get("perdedor_supuesto"), 
                                args.get("marcador")
                            )
                            
                            if res_var["status"] == "waiting":
                                respuesta = res_var["msg_reportante"]
                                # ENVIAR AL RIVAL
                                enviar_whatsapp(res_var["rival_celular"], res_var["msg_rival"])
                            else:
                                respuesta = res_var["msg"] # Error
                        
                        elif funcion == "gestionar_torneo_admin":
                            if str(numero) == str(os.getenv("ADMIN_PHONE")):
                                respuesta = gestionar_torneo_admin(db, args.get("accion"), args.get("datos"))
                            else:
                                respuesta = "❌ Solo Admin."

                if respuesta:
                    enviar_whatsapp(numero, respuesta)

    except Exception as e:
        print(f"🔥 Error: {e}")
        traceback.print_exc()
        
    return {"status": "ok"}