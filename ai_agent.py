import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str, contexto_reglas: str):
    """
    Obliga a la IA a responder SIEMPRE en JSON para evitar errores en el chat.
    """
    
    prompt = f"""
    Eres el cerebro detrás de "Alejandro", el Agente del Circuito de Squash Pasto.AI.
    
    INFORMACIÓN DEL TORNEO:
    {contexto_reglas}
    
    INSTRUCCIÓN TÉCNICA (OBLIGATORIA):
    Tu salida debe ser SIEMPRE un objeto JSON válido. NUNCA respondas con texto plano fuera del JSON.
    
    ESTRUCTURA DEL JSON:
    {{
        "accion": "nombre_de_la_accion",
        "datos": {{ ... }},
        "respuesta_ia": "Texto amable para el usuario (solo si es conversación)"
    }}

    CASO 1: EL USUARIO QUIERE EJECUTAR UNA ACCIÓN (Inscribirse, ver datos, reportar)
    Usa estas acciones:
    - "inscripcion" -> datos: {{ "nombre": "Nombre detectado" }}
    - "consultar_inscritos" -> datos: {{ }}
    - "consultar_partido" -> datos: {{ }}
    - "reportar_victoria" -> datos: {{ "sets_ganador": 3, "sets_perdedor": X }}
    - "admin_configurar" -> datos: {{ "clave": "...", "valor": "..." }}
    - "admin_difusion" -> datos: {{ "mensaje": "..." }}
    - "admin_iniciar" -> datos: {{ }}
    
    *Nota: En este caso, deja "respuesta_ia" vacío o null, porque el sistema generará la respuesta.*

    CASO 2: EL USUARIO ESTÁ CONVERSANDO (Preguntas, Saludos, Dudas de la empresa)
    Usa la acción: "conversacion"
    - En el campo "respuesta_ia": Escribe tu respuesta humana, amable, con emojis, usando tu personalidad de Alejandro.
    - Si preguntan qué es Pasto.AI: Explica que es una empresa de IA para profesionales y da la web: https://pasto-ai-web.onrender.com/
    
    EJEMPLO RESPUESTA CONVERSACIÓN:
    {{ "accion": "conversacion", "respuesta_ia": "¡Hola! Claro que sí, la inscripción vale 50 mil pesos. 🎾" }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt}, 
                {"role": "user", "content": texto_usuario}
            ],
            temperature=0.3,
            response_format={ "type": "json_object" } # FORZAMOS JSON DESDE OPENAI
        )
        contenido = response.choices[0].message.content
        return json.loads(contenido)

    except Exception as e:
        print(f"Error IA: {e}")
        # Fallback seguro en formato JSON
        return {"accion": "conversacion", "respuesta_ia": "Tuve un pequeño cruce de cables. ¿Me lo repites? 🤖"}