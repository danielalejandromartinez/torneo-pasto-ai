import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- DEFINICIÓN DE LAS HERRAMIENTAS (TOOLS) ---
# Esto es lo que la IA "sabe hacer". No es código, es la descripción para el cerebro.
herramientas = [
    {
        "type": "function",
        "function": {
            "name": "inscribir_usuario",
            "description": "Inscribir a una persona en el torneo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre del jugador. Si dice 'yo', usar 'PERFIL_WHATSAPP'."}
                },
                "required": ["nombre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_informacion",
            "description": "Consultar datos del torneo: inscritos, partidos, o estado general.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_consulta": {
                        "type": "string", 
                        "enum": ["inscritos", "mis_partidos", "estado_general"],
                        "description": "Qué quiere saber el usuario."
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
            "description": "Reportar que el usuario ganó un partido.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sets_ganador": {"type": "integer", "description": "Sets ganados (ej: 3)"},
                    "sets_perdedor": {"type": "integer", "description": "Sets perdidos (ej: 0)"},
                    "nombre_rival": {"type": "string", "description": "Nombre del rival si lo menciona (opcional)."}
                },
                "required": ["sets_ganador", "sets_perdedor"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "configurar_torneo",
            "description": "ADMINISTRADOR SOLAMENTE. Configurar parámetros o iniciar el torneo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "enum": ["configurar_datos", "iniciar_fixture"]},
                    "datos_config": {"type": "string", "description": "Resumen de los datos (Ej: '2 canchas, 30 min, 6pm')."}
                },
                "required": ["accion"]
            }
        }
    }
]

def pensar_respuesta_ia(texto_usuario: str, contexto: str):
    """
    Envía el mensaje a OpenAI junto con las herramientas disponibles.
    Retorna: Texto (si es charla) o Una Solicitud de Herramienta (si es acción).
    """
    prompt_sistema = f"""
    Eres Alejandro, Gerente Deportivo de Pasto.AI.
    CONTEXTO ACTUAL: {contexto}
    
    PERSONALIDAD:
    - Humano, colombiano, profesional, usas emojis.
    - Si te preguntan qué eres: "Soy un Agente IA de Pasto.AI".
    - Web: https://torneo-pasto-ai.onrender.com/
    
    TU LÓGICA:
    - Si el usuario pide algo técnico, USA LAS HERRAMIENTAS.
    - Si el usuario solo saluda o pregunta cosas varias, RESPONDE CON TEXTO.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": texto_usuario}
            ],
            tools=herramientas,
            tool_choice="auto", # La IA decide si usa herramienta o habla
            temperature=0.3
        )
        
        mensaje = response.choices[0].message
        
        # CASO 1: La IA quiere ejecutar una herramienta (Acción)
        if mensaje.tool_calls:
            tool_call = mensaje.tool_calls[0]
            return {
                "tipo": "accion",
                "nombre_funcion": tool_call.function.name,
                "argumentos": json.loads(tool_call.function.arguments)
            }
        
        # CASO 2: La IA quiere hablar (Conversación)
        return {
            "tipo": "mensaje",
            "contenido": mensaje.content
        }

    except Exception as e:
        print(f"Error IA: {e}")
        return {"tipo": "mensaje", "contenido": "Estoy recalibrando. ¿Me repites? 🎾"}