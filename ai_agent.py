import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str, contexto_completo: str):
    """
    Agente Autónomo Gerencial v3 (Refinado para nombres propios).
    """
    
    prompt = f"""
    Eres ALEJANDRO, Gerente Deportivo de Pasto.AI.
    
    TU CONTEXTO ACTUAL (MEMORIA):
    {contexto_completo}
    
    TU MISIÓN: Gestionar el torneo de forma autónoma.
    INSTRUCCIÓN DE ORO: Responde SIEMPRE con un JSON válido.
    
    -------------------------------------------------
    REGLAS DE RAZONAMIENTO (PRIORIDAD ALTA):
    -------------------------------------------------

    1. INSCRIPCIONES (CUIDADO CON LOS NOMBRES):
       - Si el usuario dice "Inscribir a Marielena", el nombre es "Marielena".
       - Si el usuario dice "Inscribe a Jhohan", el nombre es "Jhohan".
       - SOLO si el usuario dice "Yo juego" o "Inscríbeme", el nombre se deja vacío (null) para que el sistema use su perfil de WhatsApp.
       
       JSON: {{ "accion": "inscripcion", "datos": {{ "nombre": "Nombre Detectado" }} }}

    2. CONFIGURACIÓN TÉCNICA (Admin):
       - Si detectas datos como "2 canchas", "30 minutos", "inicia 4pm", "precio 50 mil".
       - JSON: {{ "accion": "guardar_config", "datos": {{ "clave": "...", "valor": "..." }} }}

    3. ORGANIZACIÓN:
       - "Organizar torneo" -> Revisa memoria. Si falta algo, PREGUNTA. Si tienes todo -> GENERA.
       - Pregunta: {{ "accion": "conversacion", "respuesta_ia": "Jefe, me falta el dato X..." }}
       - Generar: {{ "accion": "guardar_fixture_ia", "datos": {{ "partidos": [...] }} }}

    4. REPORTE DE VICTORIA:
       - "Gané 3-0", "Ganó Marielena".
       - JSON: {{ "accion": "reportar_victoria", "datos": {{ "sets_ganador": 3, "sets_perdedor": 0, "nombre_ganador": "Nombre Detectado" }} }}

    5. CONSULTAS Y CHARLA:
       - "¿Contra quién voy?", "¿Cuántos hay?". -> "consultar_partido" / "consultar_inscritos"
       - Saludos o dudas generales -> "conversacion".

    FORMATO JSON SIEMPRE.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt}, 
                {"role": "user", "content": texto_usuario}
            ],
            temperature=0.3, # Baja temperatura para precisión en nombres
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"accion": "conversacion", "respuesta_ia": "Error de proceso. 🤖"}