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
    obtener_contexto_completo, inscribir_jugador_tool, generar_fixture_tool,
    reportar_victoria_tool, guardar_configuracion_tool
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
        
        # Firma profesional para mensajes largos
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
                
                # Obtener nombre de WhatsApp
                nombre_wa = value.get("contacts", [{}])[0].get("profile", {}).get("name", "Usuario")
                
                print(f"📩 {nombre_wa}: {texto}")
                
                # 1. CONTEXTO
                contexto = obtener_contexto_completo(db)
                
                # 2. IA DECIDE
                decision = pensar_respuesta_ia(texto, contexto)
                
                # 3. EJECUCIÓN
                respuesta_final = ""
                
                if decision["tipo"] == "mensaje":
                    respuesta_final = decision["contenido"]
                
                elif decision["tipo"] == "accion":
                    # La IA puede mandar varias acciones a la vez, iteramos
                    for tool in decision["tool_calls"]:
                        funcion = tool.function.name
                        args = json.loads(tool.function.arguments)
                        print(f"🔧 EJECUTANDO: {funcion} -> {args}")
                        
                        res_tool = ""
                        
                        if funcion == "inscribir_usuario":
                            nombre = args.get("nombre")
                            if nombre == "PERFIL_WHATSAPP": nombre = nombre_wa
                            res_tool = inscribir_jugador_tool(db, nombre, numero)
                            if res_tool == "OK_INSCRITO":
                                respuesta_final = f"¡Listo! {nombre} ha quedado inscrito en el circuito. 🎾"
                            else:
                                respuesta_final = res_tool # Mensaje de error (ya existe)

                        elif funcion == "generar_fixture":
                            # Seguridad: Solo Admin
                            if str(numero) == str(os.getenv("ADMIN_PHONE")):
                                res_tool = generar_fixture_tool(db, args.get("partidos", []))
                                respuesta_final = f"¡Entendido Jefe! He organizado el torneo.\n{res_tool}"
                            else:
                                respuesta_final = "❌ Solo el administrador puede organizar el torneo."

                        elif funcion == "reportar_victoria":
                            res_tool = reportar_victoria_tool(
                                db, 
                                args.get("nombre_ganador"), 
                                args.get("nombre_perdedor"), 
                                args.get("marcador", "3-0")
                            )
                            if "OK" in res_tool:
                                respuesta_final = f"🔥 ¡Tremendo resultado! Victoria registrada para {args.get('nombre_ganador')}."
                            else:
                                respuesta_final = f"⚠️ {res_tool}"

                        elif funcion == "guardar_configuracion":
                            if str(numero) == str(os.getenv("ADMIN_PHONE")):
                                res_tool = guardar_configuracion_tool(db, args.get("clave"), args.get("valor"))
                                respuesta_final = "📝 Configuración actualizada."
                            else:
                                respuesta_final = "❌ Acceso denegado."
                                
                        # Si no hay respuesta definida aún
                        if not respuesta_final: respuesta_final = "Acción procesada."

                # 4. ENVIAR
                enviar_whatsapp(numero, respuesta_final)

    except Exception as e:
        print(f"🔥 Error: {e}")
        traceback.print_exc()
        
    return {"status": "ok"}