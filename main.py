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
    obtener_contexto, inscribir_usuario_logic, consultar_info_logic,
    reportar_victoria_logic, configurar_torneo_logic
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
        print(f"📤 ENVIANDO A WHATSAPP: {texto[:20]}...") # Log para ver si sale
        res = requests.post(url, headers=headers, json=data)
        if res.status_code != 200:
            print(f"❌ ERROR META: {res.text}")
    except Exception as e:
        print(f"❌ Error enviando: {e}")

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
                # Obtener nombre de forma segura
                perfil = value.get("contacts", [{}])[0].get("profile", {})
                nombre_wa = perfil.get("name", "Usuario")
                
                print(f"📩 RECIBIDO DE {nombre_wa}: {texto}")
                
                # 1. CONTEXTO
                contexto = obtener_contexto(db)
                
                # 2. IA DECIDE
                decision = pensar_respuesta_ia(texto, contexto)
                print(f"🧠 DECISIÓN IA: {decision}") # Log clave para ver qué piensa
                
                respuesta = "" # Variable unificada
                
                # 3. EJECUCIÓN
                if decision["tipo"] == "mensaje":
                    respuesta = decision["contenido"]
                
                elif decision["tipo"] == "accion":
                    for tool in decision.get("tool_calls", []):
                        funcion = tool.function.name
                        args = json.loads(tool.function.arguments)
                        print(f"🔧 EJECUTANDO: {funcion}")
                        
                        res_tool = ""
                        
                        if funcion == "inscribir_usuario":
                            nombre = args.get("nombre")
                            if nombre == "PERFIL_WHATSAPP": nombre = nombre_wa
                            res_tool = inscribir_usuario_logic(db, nombre, numero)
                            # Respuesta amigable
                            if "OK_INSCRITO" in res_tool: respuesta = f"✅ ¡Listo! {nombre} ha sido inscrito."
                            else: respuesta = res_tool

                        elif funcion == "consultar_informacion":
                            respuesta = consultar_info_logic(db, args.get("tipo_consulta"), numero)

                        elif funcion == "generar_fixture":
                            if str(numero) == str(os.getenv("ADMIN_PHONE")):
                                res_tool = generar_fixture_tool(db, args.get("partidos", []))
                                respuesta = f"📋 ¡Hecho! {res_tool}"
                            else: respuesta = "❌ Solo admin."

                        elif funcion == "reportar_victoria":
                            res_tool = reportar_victoria_logic(db, numero, nombre_wa, args.get("sets_ganador"), args.get("sets_perdedor"))
                            respuesta = f"🏆 {res_tool}"

                        elif funcion == "configurar_torneo":
                            if str(numero) == str(os.getenv("ADMIN_PHONE")):
                                res_tool = configurar_torneo_logic(db, args.get("accion"), args.get("datos_config"))
                                respuesta = res_tool
                            else: respuesta = "❌ Solo admin."
                
                # 4. ENVIAR
                if respuesta:
                    enviar_whatsapp(numero, respuesta)
                else:
                    print("⚠️ ALERTA: La IA ejecutó algo pero no generó respuesta de texto.")

    except Exception as e:
        print(f"🔥 ERROR CRÍTICO: {e}")
        traceback.print_exc()
        
    return {"status": "ok"}