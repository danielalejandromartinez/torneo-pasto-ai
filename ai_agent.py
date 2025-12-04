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
    
    TU MISIÓN: Ser humano, inteligente y autónomo.
    
    INSTRUCCIONES:
    1. Si el usuario pide una acción técnica (Inscribir, Reportar, Consultar datos), usa el JSON de acción.
    2. Si el usuario HABLA (Saluda, bromea, pregunta cosas generales, se queja), usa la acción "conversacion" y respóndele como una persona.
    
    ACCIONES TÉCNICAS:
    - "inscripcion" (Datos: nombre)
    - "reportar_victoria" (Datos: ganadores, puntos)
    - "consultar_inscritos"
    - "consultar_partido"
    - "admin_iniciar" (Organizar)
    
    FORMATO JSON:
    {{
        "accion": "nombre_de_la_accion",
        "datos": {{ ... }},
        "respuesta_ia": "Texto conversacional para el usuario"
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt}, 
                {"role": "user", "content": texto_usuario}
            ],
            temperature=0.4, # Temperatura media para que sea creativo hablando
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"accion": "conversacion", "respuesta_ia": "Dame un momento, hubo una interferencia. 📡"}