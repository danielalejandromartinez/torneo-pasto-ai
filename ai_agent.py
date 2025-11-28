import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str):
    print(f"🤖 IA Analizando: '{texto_usuario}'...")

    prompt_sistema = """
    Eres el Árbitro Inteligente de un torneo de Squash.
    Tu trabajo es leer mensajes de WhatsApp y extraer resultados.
    
    CONTEXTO CULTURAL:
    - Los usuarios usan jerga colombiana. Palabras como "Parce", "Mani", "Bro", "Hola", "Oye" al inicio NO son nombres, son saludos. IGNÓRALOS.
    - Si el mensaje dice "Gané", "Le gané", "Victoria", el ganador es el remitente (retorna "Yo").
    
    TU MISIÓN:
    Si el mensaje es un reporte de resultado, devuelve un JSON así:
    {
        "intencion": "reportar_victoria",
        "ganador": "Nombre EXACTO del rival o 'Yo'",
        "sets_ganador": 3,
        "sets_perdedor": 1
    }

    Si NO es un resultado claro, devuelve:
    {
        "intencion": "otra",
        "respuesta": "No entendí el resultado. Ejemplo: 'Gané 3-0 a Pedro'"
    }
    """

    try:
        respuesta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": texto_usuario}
            ],
            temperature=0
        )
        
        contenido = respuesta.choices[0].message.content
        contenido = contenido.replace("```json", "").replace("```", "")
        
        datos = json.loads(contenido)
        return datos

    except Exception as e:
        print(f"❌ Error en la IA: {e}")
        return {"intencion": "error"}