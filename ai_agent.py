import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- DEFINICIÓN DE HABILIDADES (TOOLS) ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "inscribir_jugador",
            "description": "Inscribir un nuevo participante.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre real del jugador. Si dice 'yo', usar 'PERFIL_WHATSAPP'."}
                },
                "required": ["nombre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generar_fixture",
            "description": "Crear los partidos automáticamente basado en los inscritos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "partidos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "j1_nombre": {"type": "string"},
                                "j2_nombre": {"type": "string"},
                                "hora": {"type": "string"},
                                "cancha": {"type": "string"}
                            }
                        },
                        "description": "Lista de partidos que tú (IA) decides crear."
                    }
                },
                "required": ["partidos"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reportar_victoria",
            "description": "Registrar un resultado de partido.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_ganador": {"type": "string"},
                    "nombre_perdedor": {"type": "string"},
                    "marcador": {"type": "string"}
                },
                "required": ["nombre_ganador", "nombre_perdedor", "marcador"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "guardar_configuracion",
            "description": "Guardar datos técnicos del torneo (canchas, horas, reglas).",
            "parameters": {
                "type": "object",
                "properties": {
                    "clave": {"type": "string"},
                    "valor": {"type": "string"}
                },
                "required": ["clave", "valor"]
            }
        }
    }
]

def pensar_respuesta_ia(texto_usuario: str, contexto: str):
    prompt_sistema = f"""
    Eres ALEJANDRO, el Director Deportivo de Pasto.AI.
    
    TU CONTEXTO ACTUAL:
    {contexto}
    
    TU PERSONALIDAD:
    - Humano, colombiano, profesional, estratega.
    - NO eres un robot. Habla con fluidez.
    - Si te preguntan algo que está en tu contexto, respóndelo con tus palabras.
    - Si falta información para organizar (ej: no sabes cuántas canchas), PREGÚNTALE al usuario.
    
    TU LÓGICA DE NEGOCIO:
    1. El Ranking es sagrado. Gana quien reta y vence.
    2. Organizar: Si te piden organizar, revisa los inscritos en el contexto y GENERA tú mismo los cruces usando la herramienta 'generar_fixture'.
    3. Si alguien dice "Gané", busca en el contexto contra quién jugaba y usa la herramienta 'reportar_victoria'.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": texto_usuario}
            ],
            tools=tools,
            tool_choice="auto", 
            temperature=0.4
        )
        
        mensaje = response.choices[0].message
        
        # Si la IA decide usar una herramienta
        if mensaje.tool_calls:
            return {
                "tipo": "accion",
                "tool_calls": mensaje.tool_calls
            }
        
        # Si la IA decide hablar
        return {
            "tipo": "mensaje",
            "contenido": mensaje.content
        }

    except Exception as e:
        print(f"Error IA: {e}")
        return {"tipo": "mensaje", "contenido": "Dame un momento, estoy pensando... 🧠"}