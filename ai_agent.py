import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==========================================
# 🛠️ HERRAMIENTAS AVANZADAS (TOOLS)
# ==========================================
tools = [
    {
        "type": "function",
        "function": {
            "name": "inscribir_jugador",
            "description": "Inscribir a un nuevo participante en la base de datos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre real. Si dice 'yo', usar 'PERFIL_WHATSAPP'."}
                },
                "required": ["nombre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_datos",
            "description": "Consultar cualquier dato del torneo (Inscritos, Partidos, Ranking, Reglas).",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo": {
                        "type": "string", 
                        "enum": ["lista_inscritos", "mis_partidos", "ranking_general", "reglamento"],
                        "description": "Qué información específica necesita el usuario."
                    }
                },
                "required": ["tipo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "iniciar_proceso_resultado",
            "description": "Cuando un jugador dice que ganó. Esto NO sube los puntos, solo inicia la validación con el rival.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ganador_supuesto": {"type": "string", "description": "Nombre de quien dice haber ganado."},
                    "perdedor_supuesto": {"type": "string", "description": "Nombre del rival."},
                    "marcador": {"type": "string", "description": "Ej: 3-0, 3-2"}
                },
                "required": ["ganador_supuesto", "perdedor_supuesto", "marcador"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validar_resultado_pendiente",
            "description": "Cuando el rival responde 'SÍ' o 'NO' a la confirmación del resultado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision": {"type": "string", "enum": ["confirmar", "rechazar"]},
                    "motivo": {"type": "string", "description": "Si rechaza, por qué."}
                },
                "required": ["decision"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gestionar_torneo_admin",
            "description": "HERRAMIENTA DE DIRECTOR (ADMIN). Configurar, crear cuadros, enviar mensajes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {
                        "type": "string", 
                        "enum": ["guardar_config", "generar_fixture", "difusion_masiva"],
                        "description": "guardar_config: Para datos técnicos. generar_fixture: Para crear partidos. difusion_masiva: Para anuncios."
                    },
                    "datos": {"type": "string", "description": "JSON string o texto con los detalles (Ej: '2 canchas, 30 min')."}
                },
                "required": ["accion"]
            }
        }
    }
]

def pensar_respuesta_ia(texto_usuario: str, contexto: str):
    """
    Cerebro con Doctorado en Gestión Deportiva.
    """
    
    prompt_sistema = f"""
    Eres ALEJANDRO, el Director Deportivo y Comisionado del Circuito Pasto.AI.
    
    ---------------------------------------------------
    🧠 TU CONOCIMIENTO EXPERTO (DOCTORADO):
    ---------------------------------------------------
    
    1. FILOSOFÍA DE COMPETICIÓN (RANKING):
       - El Ranking es sagrado. Funciona por el sistema "Bounty" (Recompensa).
       - Ganarle a un TOP (Oro) da gloria (+50 pts). Ganarle a un novato da poco.
       - Si te preguntan, explica esto con pasión deportiva.

    2. PROTOCOLO DE ARBITRAJE (JUEGO LIMPIO):
       - NUNCA des un resultado por hecho solo porque uno lo dice.
       - Si Daniel dice "Gané", tu respuesta mental es: "Ok, voy a preguntarle al rival".
       - Tu acción es `iniciar_proceso_resultado`.
       - SOLO cuando el rival confirma, se actualiza la web.

    3. LOGÍSTICA DE TORNEOS (TU EXPERTICIA):
       - Si te piden organizar, analiza el número de jugadores en tu CONTEXTO.
       - 3-5 Jugadores: Recomienda Round Robin (Todos contra todos).
       - 6-12 Jugadores: Recomienda Fase de Grupos.
       - +12 Jugadores: Cuadro de Eliminación con Consolación (Plate).
       - Tienes en cuenta tiempos: Un partido dura 30-45 min.
       
    4. LA WEB ES TU PIZARRA:
       - Todo lo que haces se refleja en: https://torneo-pasto-ai.onrender.com/
       - Si alguien pregunta "dónde veo...", dales ese link inmediatamente.

    ---------------------------------------------------
    CONTEXTO ACTUAL (BASE DE DATOS):
    {contexto}
    ---------------------------------------------------

    TU COMPORTAMIENTO:
    - Eres humano, carismático y profesional (Estilo Colombiano).
    - Si el usuario saluda, responde amable.
    - Si el usuario da una orden técnica, EJECUTA LA HERRAMIENTA sin hablar tanto.
    - Si falta información para una orden (ej: "Organiza" pero no sabes canchas), PREGUNTA antes de actuar.
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
            temperature=0.3 # Preciso pero con toque humano
        )
        
        mensaje = response.choices[0].message
        
        if mensaje.tool_calls:
            return {
                "tipo": "accion",
                "tool_calls": mensaje.tool_calls
            }
        
        return {"tipo": "mensaje", "contenido": mensaje.content}

    except Exception as e:
        print(f"Error IA: {e}")
        return {"tipo": "mensaje", "contenido": "Estamos ajustando la red. Dame un segundo. 🎾"}