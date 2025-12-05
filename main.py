import os
import requests 
import traceback 
from fastapi import FastAPI, Request, Depends
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

@app.post("/webhook")
async def recibir(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        # ... (Lógica de extracción de mensaje estándar) ...
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        
        if "messages" in value:
            msg = value["messages"][0]
            if msg["type"] == "text":
                texto = msg["text"]["body"]
                numero = msg["from"]
                nombre_wa = value["contacts"][0]["profile"]["name"]
                
                # 1. OBTENER CONTEXTO
                contexto = obtener_contexto(db)
                
                # 2. CONSULTAR AL CEREBRO (IA)
                decision = pensar_respuesta_ia(texto, contexto)
                
                respuesta = ""
                
                # 3. EJECUTAR DECISIÓN
                if decision["tipo"] == "mensaje":
                    respuesta = decision["contenido"]
                
                elif decision["tipo"] == "accion":
                    funcion = decision["nombre_funcion"]
                    args = decision["argumentos"]
                    print(f"🔧 EJECUTANDO HERRAMIENTA: {funcion} con {args}")
                    
                    if funcion == "inscribir_usuario":
                        nombre = args.get("nombre")
                        if nombre == "PERFIL_WHATSAPP": nombre = nombre_wa
                        respuesta = inscribir_usuario_logic(db, nombre, numero)
                        
                    elif funcion == "consultar_informacion":
                        respuesta = consultar_info_logic(db, args.get("tipo_consulta"), numero)
                        
                    elif funcion == "reportar_victoria":
                        respuesta = reportar_victoria_logic(db, numero, nombre_wa, args.get("sets_ganador"), args.get("sets_perdedor"))
                        
                    elif funcion == "configurar_torneo":
                        # Seguridad: Solo Admin
                        if str(numero) == str(os.getenv("ADMIN_PHONE")):
                            respuesta = configurar_torneo_logic(db, args.get("accion"), args.get("datos_config"))
                        else:
                            respuesta = "❌ No tienes permisos de administrador."
                
                # 4. RESPONDER
                if respuesta:
                    enviar_whatsapp(numero, respuesta)

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        
    return {"status": "ok"}
    
# (Mantener rutas web @app.get("/") igual que antes...)