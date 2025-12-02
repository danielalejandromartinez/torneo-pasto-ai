import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str, contexto_reglas: str):
    prompt = f"""
    Eres ALEJANDRO, el Agente IA de Pasto.AI.
    
    INFO TORNEO:
    {contexto_reglas}
    
    INSTRUCCIÓN: Responde SIEMPRE con JSON.
    
    ESTRUCTURA JSON:
    {{
        "accion": "nombre_accion",
        "datos": {{ ... }},
        "respuesta_ia": "Texto conversacional (solo si accion es 'conversacion')"
    }}

    INTENCIONES:
    
    1. INSCRIPCIÓN:
       - "Inscribir a Miguel", "Quiero jugar soy Daniel".
       - JSON: {{ "accion": "inscripcion", "datos": {{ "nombre": "Nombre Detectado" }} }}
       *IMPORTANTE: Extrae el nombre propio limpio.*

    2. REPORTAR VICTORIA:
       - "Gané 3-0", "Miguel ganó", "Victoria de Daniel".
       - JSON: {{ "accion": "reportar_victoria", "datos": {{ "sets_ganador": 3, "sets_perdedor": 0, "nombre_ganador": "Nombre Detectado (Opcional)" }} }}
       *Si dice "Gané", nombre_ganador va vacío. Si dice "Miguel ganó", pon "Miguel".*

    3. CONSULTAS:
       - "¿A qué hora juego?", "Mis partidos". -> "consultar_partido"
       - "¿Cuántos inscritos?", "Estadísticas". -> "consultar_inscritos"

    4. ADMIN (Solo Jefe):
       - "Configurar...", "Enviar mensaje...", "Iniciar torneo".
       - Acciones: "admin_configurar", "admin_difusion", "admin_iniciar".

    5. CONVERSACIÓN GENERAL:
       - Saludos, preguntas de la empresa.
       - JSON: {{ "accion": "conversacion", "respuesta_ia": "Tu respuesta amable..." }}
       - Web: https://pasto-ai-web.onrender.com/
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": texto_usuario}],
            temperature=0,
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"accion": "conversacion", "respuesta_ia": "Error de conexión cerebral. 🤖"}