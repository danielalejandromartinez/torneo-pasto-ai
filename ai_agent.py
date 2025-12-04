import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str, contexto_completo: str):
    prompt = f"""
    Eres ALEJANDRO, el Gerente Deportivo de Pasto.AI.
    
    CONTEXTO: {contexto_completo}
    
    TU MISIÓN: Entender la intención del usuario.
    
    🚨 REGLA DE PRIORIDAD:
    Si el usuario hace una PREGUNTA ("¿Cuántos hay?", "Dame la lista", "¿Quiénes están?", "¿Qué horas?", "Info"),
    TU ACCIÓN DEBE SER 'consultar_inscritos' o 'conversacion'.
    NO USES 'admin_wizard' PARA PREGUNTAS.

    INTENCIONES:
    
    1. CONSULTAR INSCRITOS (PRIORIDAD ALTA):
       - "Dame los nombres", "¿Quiénes están?", "¿Cuántos inscritos hay?", "Lista de jugadores".
       - JSON: {{ "accion": "consultar_inscritos" }}

    2. CONSULTAR PARTIDO:
       - "¿A qué hora juego?", "Mis partidos".
       - JSON: {{ "accion": "consultar_partido" }}

    3. INSCRIPCIÓN:
       - "Inscribir a X", "Quiero jugar".
       - JSON: {{ "accion": "inscripcion", "datos": {{ "nombre": "..." }} }}

    4. REPORTAR VICTORIA:
       - "Gané 3-0".
       - JSON: {{ "accion": "reportar_victoria", "datos": {{ ... }} }}

    5. WIZARD ORGANIZADOR (SOLO DATOS TÉCNICOS):
       - ÚSALO SOLO SI el usuario responde con números o datos cortos: "2", "30", "15:00", "Generar", "Cancelar".
       - O si dice explícitamente "Organizar torneo".
       - JSON: {{ "accion": "admin_wizard", "datos": {{ "mensaje": "{texto_usuario}" }} }}

    6. CHARLA / VENTAS:
       - Saludos, dudas generales, link de la web.
       - JSON: {{ "accion": "conversacion", "respuesta_ia": "..." }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": texto_usuario}],
            temperature=0.2, 
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"accion": "conversacion", "respuesta_ia": "Error."}