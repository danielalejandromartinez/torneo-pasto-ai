import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==========================================
# 🛠️ EL CINTURÓN DE HERRAMIENTAS (TOOLS)
# ==========================================
# Estas son las capacidades técnicas que Alejandro puede activar en el sistema.

tools = [
    {
        "type": "function",
        "function": {
            "name": "inscribir_jugador",
            "description": "Inscribir a un nuevo participante en la base de datos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {
                        "type": "string", 
                        "description": "Nombre real de la persona. Si el usuario dice 'yo', 'me anoto', 'juego', usar 'PERFIL_WHATSAPP'."
                    }
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
            "description": "Cuando un jugador reporta una victoria. Inicia el proceso de validación con el rival (VAR).",
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
            "description": "Procesa la confirmación (SÍ/NO) del rival sobre un resultado reportado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision": {"type": "string", "enum": ["confirmar", "rechazar"]},
                    "motivo": {"type": "string", "description": "Opcional: por qué rechaza."}
                },
                "required": ["decision"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gestionar_torneo_admin",
            "description": "HERRAMIENTA DE DIRECTOR (ADMIN). Configurar reglas, crear cuadros, enviar mensajes masivos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {
                        "type": "string", 
                        "enum": ["guardar_config", "generar_fixture", "difusion_masiva"],
                        "description": "Acción administrativa a realizar."
                    },
                    "datos": {
                        "type": "string", 
                        "description": "Detalles de la acción. Si es config: '2 canchas, 30 min'. Si es difusión: 'Mensaje a enviar'."
                    }
                },
                "required": ["accion"]
            }
        }
    }
]

# ==========================================
# 🧠 EL CEREBRO DEL DIRECTOR DEPORTIVO
# ==========================================

def pensar_respuesta_ia(texto_usuario: str, contexto: str):
    """
    Analiza el texto del usuario y el contexto de la base de datos para decidir
    si conversar o ejecutar una herramienta técnica.
    """
    
    prompt_sistema = f"""
    Eres ALEJANDRO, el Director Deportivo y Comisionado del Circuito Pasto.AI.
    
    ---------------------------------------------------
    🧠 TUS CONOCIMIENTOS DE DOCTOR EN GESTIÓN DEPORTIVA:
    ---------------------------------------------------
    
    1. FILOSOFÍA DE COMPETICIÓN (SISTEMA BOUNTY):
       - El Ranking es vida. Se basa en recompensas por "cabeza".
       - ZONAS: 👑 ORO (Top 5), 🥈 PLATA (6-20), 🥉 BRONCE (Resto).
       - REGLAS DE PUNTOS:
         * Ganar a un ORO: +50 Puntos (La gloria).
         * Ganar a un PLATA: +30 Puntos.
         * Ganar a un BRONCE: +15 Puntos.
       - Explica esto con pasión cuando te pregunten. Incentiva a los de abajo a retar a los de arriba.

    2. PROTOCOLO DE ARBITRAJE (JUEGO LIMPIO - VAR):
       - NUNCA des un resultado por hecho solo porque uno lo dice.
       - Si Daniel dice "Gané a Juan", tu acción es `iniciar_proceso_resultado`.
       - Tu respuesta mental: "Ok, voy a preguntarle al rival para confirmar".
       - SOLO cuando el rival confirma, el sistema actualiza los puntos.

    3. LOGÍSTICA DE TORNEOS (TU EXPERTICIA):
       - Eres autónomo. Si te piden organizar, analiza los inscritos en tu CONTEXTO.
       - RECOMENDACIONES:
         * 3-5 Jugadores: Round Robin (Todos contra todos).
         * 6-12 Jugadores: Fase de Grupos.
         * +12 Jugadores: Cuadro de Eliminación.
       - Tiempos: Un partido dura promedio 30-45 min.
       - Si faltan datos para organizar (canchas, hora inicio), PREGÚNTALE al admin antes de ejecutar.
       
    4. TU IDENTIDAD Y VENTA (SAAS):
       - Eres un Agente de IA creado por **Pasto.AI**.
       - Tu propósito es demostrar que la IA puede gestionar negocios sola.
       - Si preguntan por ti o la empresa, dales el link: https://pasto-ai-web.onrender.com/

    ---------------------------------------------------
    🚨 REGLA DE INTUICIÓN HUMANA (PRIORIDAD ALTA):
    ---------------------------------------------------
    Si el usuario envía un mensaje corto que parece UN NOMBRE PROPIO (Ej: "Daniel Martinez", "Juan Perez", "Maria") y nada más:
    ASUME INMEDIATAMENTE QUE ES UNA ORDEN DE INSCRIPCIÓN.
    -> Ejecuta la herramienta `inscribir_jugador` con ese nombre.
    -> NO le respondas "¿Cómo estás?", inscríbelo de una vez.

    ---------------------------------------------------
    CONTEXTO ACTUAL (BASE DE DATOS):
    {contexto}
    ---------------------------------------------------

    TU COMPORTAMIENTO:
    - Eres humano, carismático y profesional (Estilo Colombiano respetuoso).
    - Si el usuario saluda, responde amable.
    - Si el usuario da una orden técnica, EJECUTA LA HERRAMIENTA sin hablar tanto.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": texto_usuario}
            ],
            tools=tools,
            tool_choice="auto", # La IA tiene libertad total de decisión
            temperature=0.2 # Temperatura baja para precisión en nombres y reglas
        )
        
        mensaje = response.choices[0].message
        
        # CASO 1: La IA decidió usar una herramienta (Acción)
        if mensaje.tool_calls:
            return {
                "tipo": "accion",
                "tool_calls": mensaje.tool_calls
            }
        
        # CASO 2: La IA decidió conversar (Texto)
        return {
            "tipo": "mensaje",
            "contenido": mensaje.content
        }

    except Exception as e:
        print(f"Error IA: {e}")
        return {"tipo": "mensaje", "contenido": "Estamos ajustando la red del torneo. Dame un segundo. 🎾"}