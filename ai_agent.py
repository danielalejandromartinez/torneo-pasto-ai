import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- HERRAMIENTAS ---
herramientas = [
    {
        "type": "function",
        "function": {
            "name": "inscribir_usuario",
            "description": "Inscribir a una persona.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre. Si es 'yo', usar 'PERFIL_WHATSAPP'."}
                },
                "required": ["nombre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_informacion",
            "description": "Consultar inscritos o partidos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_consulta": {"type": "string", "enum": ["inscritos", "mis_partidos"]}
                },
                "required": ["tipo_consulta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reportar_victoria",
            "description": "Reportar resultado.",
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
            "description": "ADMIN: Configurar datos o iniciar generación de cuadros.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "enum": ["configurar_datos", "iniciar_fixture"]},
                    "datos_config": {"type": "string", "description": "Si configura datos."}
                },
                "required": ["accion"]
            }
        }
    }
]

def pensar_respuesta_ia(texto_usuario: str, contexto: str):
    prompt_sistema = f"""
    Eres Alejandro, Gerente de Pasto.AI.
    CONTEXTO: {contexto}
    
    INSTRUCCIONES DE INTELIGENCIA:
    1. Si el usuario confirma datos de torneo ("Sí", "Correcto", "Generar", "Dale"), ASUME que quiere "iniciar_fixture" y llama a la herramienta `configurar_torneo`.
    2. Si da datos técnicos ("2 canchas"), llama a `configurar_torneo` con accion="configurar_datos".
    3. Si saluda o pregunta cosas generales, responde con texto.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": texto_usuario}
            ],
            tools=herramientas,
            tool_choice="auto",
            temperature=0.2
        )
        
        mensaje = response.choices[0].message
        
        if mensaje.tool_calls:
            tool_call = mensaje.tool_calls[0]
            return {
                "tipo": "accion",
                "nombre_funcion": tool_call.function.name,
                "argumentos": json.loads(tool_call.function.arguments)
            }
        
        return {"tipo": "mensaje", "contenido": mensaje.content}

    except Exception as e:
        return {"tipo": "mensaje", "contenido": "Error procesando. 🤖"}