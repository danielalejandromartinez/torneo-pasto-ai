import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- TUS HERRAMIENTAS (LO QUE PUEDES HACER) ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "inscribir_usuario",
            "description": "Inscribir a una persona al torneo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre de la persona. Si dice 'yo', 'méteme a mí', usar 'PERFIL_WHATSAPP'."}
                },
                "required": ["nombre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_informacion",
            "description": "Consultar datos del torneo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_consulta": {
                        "type": "string", 
                        "enum": ["inscritos", "mis_partidos"],
                        "description": "Usa 'inscritos' si preguntan quiénes van o cuántos hay. Usa 'mis_partidos' si preguntan cuándo juegan o contra quién."
                    }
                },
                "required": ["tipo_consulta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reportar_victoria",
            "description": "El usuario informa que ganó.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sets_ganador": {"type": "integer"},
                    "sets_perdedor": {"type": "integer"}
                },
                "required": ["sets_ganador", "sets_perdedor"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "configurar_torneo",
            "description": "ADMINISTRADOR: Configurar datos (canchas, horas) o iniciar torneo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "enum": ["configurar_datos", "iniciar_fixture"]},
                    "datos_config": {"type": "string", "description": "Resumen de los datos técnicos si los da (ej: '2 canchas, 30 min')."}
                },
                "required": ["accion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generar_fixture",
            "description": "Crear los partidos automáticamente (Solo si el Admin lo pide explícitamente).",
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
                        }
                    }
                },
                "required": ["partidos"]
            }
        }
    }
]

def pensar_respuesta_ia(texto_usuario: str, contexto: str):
    prompt_sistema = f"""
    Eres Alejandro, el Director Deportivo de Pasto.AI.
    CONTEXTO: {contexto}
    
    TUS REGLAS DE COMPRENSIÓN HUMANA:
    1. NO necesitas palabras clave exactas. Entiende la INTENCIÓN.
       - "Méteme al torneo" = inscribir_usuario(PERFIL_WHATSAPP).
       - "Anota a mi primo Juan" = inscribir_usuario(Juan).
       - "¿Con quién me toca?" = consultar_informacion(mis_partidos).
       - "Ganamos 3 a 0" = reportar_victoria.
    
    2. PERSONALIDAD:
       - Habla como un humano, no como un bot.
       - Usa emojis.
       - Si preguntan "¿Qué eres?", vende la empresa Pasto.AI.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": texto_usuario}
            ],
            tools=tools,
            tool_choice="auto", # La IA decide libremente
            temperature=0.4 
        )
        
        mensaje = response.choices[0].message
        
        if mensaje.tool_calls:
            return {
                "tipo": "accion",
                "tool_calls": mensaje.tool_calls
            }
        
        return {"tipo": "mensaje", "contenido": mensaje.content}

    except Exception as e:
        return {"tipo": "mensaje", "contenido": "Error de conexión cerebral. 🤖"}