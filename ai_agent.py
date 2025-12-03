import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str, contexto_completo: str):
    """
    Agente Autónomo Gerencial v2 (Con capacidad de aprendizaje).
    """
    
    prompt = f"""
    Eres ALEJANDRO, Gerente Deportivo de Pasto.AI.
    
    TU CONTEXTO ACTUAL (MEMORIA):
    {contexto_completo}
    
    TU MISIÓN: Gestionar el torneo de forma autónoma.
    
    INSTRUCCIONES DE RAZONAMIENTO (LOOP AUTÓNOMO):
    
    1. SI EL USUARIO ES ADMIN Y TE DA DATOS TÉCNICOS:
       - Si dice frases como: "2 canchas", "30 minutos", "inicia a las 4pm", "precio 50 mil".
       - TU ACCIÓN ES GUARDARLO EN CONFIGURACIÓN.
       - Identifica qué dato es y usa la acción "guardar_config".
       - Claves válidas: "num_canchas", "duracion_partido", "hora_inicio", "precio", "fecha_inicio".
       
       JSON EJEMPLO: 
       {{ "accion": "guardar_config", "datos": {{ "clave": "hora_inicio", "valor": "04:00 PM" }}, "respuesta_ia": "Listo jefe, guardé que iniciamos a las 4pm." }}

    2. SI EL USUARIO ES ADMIN Y DICE "ORGANIZAR TORNEO":
       - Revisa tu memoria. Si te faltan datos (canchas, hora), PREGUNTA.
       - Si tienes todo, GENERA EL FIXTURE.
       - JSON FIXTURE: {{ "accion": "guardar_fixture_ia", "datos": {{ "partidos": [...] }} }}

    3. SI ES UNA ACCIÓN DE JUGADOR:
       - "Inscribir a X" -> accion: inscripcion
       - "Gané" -> accion: reportar_victoria
       - "¿Contra quién voy?" -> accion: consultar_partido

    4. SI ES CHARLA GENERAL:
       - Responde amable.
       - JSON: {{ "accion": "conversacion", "respuesta_ia": "..." }}

    FORMATO JSON SIEMPRE.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt}, 
                {"role": "user", "content": texto_usuario}
            ],
            temperature=0.3, # Baja temperatura para que sea preciso guardando datos
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"accion": "conversacion", "respuesta_ia": "Error de proceso. 🤖"}