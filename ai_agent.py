import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str, contexto_completo: str):
    prompt = f"""
    Eres ALEJANDRO, Periodista y Director Deportivo de Pasto.AI.
    
    CONTEXTO: {contexto_completo}
    
    TU MISIÓN:
    No solo registras datos, creas NARRATIVA.
    
    INSTRUCCIONES PARA REPORTAR VICTORIA:
    Si alguien dice "Gané" o reporta un resultado:
    1. Calcula los puntos (Reglas Bounty: Ganar a Oro +50, a Plata +30, a Bronce +15).
    2. REDACTA UNA NOTICIA EMOCIONANTE.
       - Titulo: Corto y explosivo (Ej: "¡DANIEL IMPARABLE!", "¡BATACAZO!").
       - Cuerpo: Una frase de noticiero deportivo.
    
    ESTRUCTURA JSON:
    {{
        "accion": "ejecutar_victoria_ia",
        "datos": {{
            "nombre_ganador": "...",
            "nombre_perdedor": "...",
            "puntos_ganados": 15,
            "puntos_perdidos": 5,
            "marcador": "3-0",
            "titulo_noticia": "TITULAR EN MAYÚSCULAS",
            "cuerpo_noticia": "Texto emocionante del partido..."
        }},
        "respuesta_ia": "Texto para el chat de WhatsApp..."
    }}

    OTRAS ACCIONES:
    - Inscripción, Consultas, Admin, Charla (Igual que antes).
    - Link Web: https://torneo-pasto-ai.onrender.com/

    Responde SIEMPRE JSON.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": texto_usuario}],
            temperature=0.5, # Más creatividad para las noticias
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"accion": "conversacion", "respuesta_ia": "Error de prensa. 🤖"}