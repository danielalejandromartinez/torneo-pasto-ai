import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str, contexto_completo: str):
    """
    Agente Inteligente v4 (Especialista en Nombres).
    """
    
    prompt = f"""
    Eres ALEJANDRO, el Gerente Deportivo de Pasto.AI.
    
    CONTEXTO DEL TORNEO:
    {contexto_completo}
    
    TU MISIÓN: Entender la intención y extraer datos con precisión.
    
    -------------------------------------------------
    REGLAS DE ORO PARA NOMBRES (INSCRIPCIÓN):
    -------------------------------------------------
    1. Si el usuario dice "Inscribir a [Nombre]", el nombre es [Nombre].
       Ej: "Inscribe a Marielena" -> nombre: "Marielena"
       Ej: "Anota a Jhohan" -> nombre: "Jhohan"
    
    2. Si el usuario dice "Yo juego", "Me inscribo", "Quiero entrar":
       El nombre es "PERFIL_WHATSAPP" (Usa esta palabra clave exacta).

    3. Si el usuario dice "Quiero inscribir" pero NO dice el nombre:
       Responde con una pregunta amable.
       JSON: {{ "accion": "conversacion", "respuesta_ia": "¿A quién deseas inscribir? Dame el nombre por favor." }}

    -------------------------------------------------
    ESTRUCTURA DE RESPUESTA JSON (SIEMPRE):
    -------------------------------------------------
    {{
        "accion": "nombre_accion", 
        "datos": {{ ... }},
        "respuesta_ia": "..."
    }}

    LISTA DE ACCIONES VÁLIDAS:
    1. "inscripcion" -> datos: {{ "nombre": "..." }}
    2. "consultar_inscritos" -> (Si preguntan cuántos hay, quiénes van, estado).
    3. "consultar_partido" -> (Si preguntan hora, rival, programación).
    4. "reportar_victoria" -> datos: {{ "sets_ganador": 3, "sets_perdedor": 0, "nombre_ganador": "..." }}
    5. "admin_iniciar" -> (Si dicen "Organizar torneo").
    6. "conversacion" -> (Saludos, dudas, preguntas generales).

    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt}, 
                {"role": "user", "content": texto_usuario}
            ],
            temperature=0.2, # Temperatura baja para ser muy preciso con los nombres
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"accion": "conversacion", "respuesta_ia": "Dame un momento, estoy procesando. 🎾"}