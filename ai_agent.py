import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str, contexto_completo: str):
    prompt = f"""
    Eres ALEJANDRO, el Gerente Deportivo de Pasto.AI.
    CONTEXTO: {contexto_completo}
    
    TU OBJETIVO: Clasificar la intención del usuario con PRIORIDAD INTELIGENTE.
    
    🚨 REGLAS DE PRIORIDAD (LEER CON ATENCIÓN):
    
    1. SI EL USUARIO DA UNA ORDEN CLARA (Inscribir, Reportar, Consultar):
       - ESTO TIENE PRIORIDAD MÁXIMA sobre cualquier configuración pendiente.
       - Si dice "Inscribir a Juan", la acción ES "inscripcion". NO es "admin_wizard".
       - Si dice "Gané", la acción ES "reportar_victoria".
       
    2. WIZARD ORGANIZADOR (Solo si es respuesta técnica):
       - Solo usa la acción 'admin_wizard' si el usuario responde con:
         * Un número solo ("2", "30").
         * Una hora ("15:00").
         * Palabras de confirmación ("Generar", "Sí").
         * Comandos de salida ("Cancelar", "Salir").
       - O si dice explícitamente "Organizar torneo".

    ------------------------------------
    LISTA DE ACCIONES (JSON):
    ------------------------------------
    
    A. "inscripcion":
       - Texto: "Inscribir a [Nombre]", "Quiero jugar soy [Nombre]".
       - JSON: {{ "accion": "inscripcion", "datos": {{ "nombre": "Nombre Detectado" }} }}

    B. "reportar_victoria":
       - Texto: "Gané 3-0", "Ganamos", "Victoria de [Nombre]".
       - JSON: {{ "accion": "reportar_victoria", "datos": {{ "sets_ganador": 3, "sets_perdedor": 0, "nombre_ganador": "Nombre Detectado" }} }}

    C. "consultar_inscritos":
       - Texto: "¿Cuántos hay?", "¿Quiénes están?", "Dame la lista".
       - JSON: {{ "accion": "consultar_inscritos" }}

    D. "consultar_partido":
       - Texto: "¿A qué hora juego?", "Mi programación".
       - JSON: {{ "accion": "consultar_partido" }}

    E. "admin_wizard":
       - Texto: "Organizar torneo", "2", "30", "16:00", "Generar", "Cancelar".
       - JSON: {{ "accion": "admin_wizard", "datos": {{ "mensaje": "{texto_usuario}" }} }}

    F. "conversacion":
       - Saludos, dudas generales, preguntas sobre la empresa.
       - JSON: {{ "accion": "conversacion", "respuesta_ia": "..." }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": texto_usuario}],
            temperature=0.1, # Temperatura MUY BAJA para que sea obediente y no creativo
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"accion": "conversacion", "respuesta_ia": "Error."}