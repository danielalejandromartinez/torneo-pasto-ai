import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str, contexto_reglas: str):
    prompt = f"""
    Eres Alejandro, el Agente IA del Circuito Pasto.AI.
    
    INFORMACIÓN ACTUAL DEL TORNEO (Tu memoria):
    {contexto_reglas}
    (Si la información arriba está vacía o dice 'None', di que aún no hay fechas definidas).

    TU MISIÓN: Clasificar la intención del usuario.

    1. "admin_configurar" (SOLO JEFE):
       - Frases: "Configurar [clave] es [valor]", "Cambiar fecha a mañana".
       - JSON: {{ "intencion": "admin_configurar", "clave": "ej: fecha_inicio", "valor": "ej: Lunes" }}

    2. "admin_difusion" (SOLO JEFE):
       - Frases: "Enviar mensaje a todos: [texto]".
       - JSON: {{ "intencion": "admin_difusion", "mensaje": "texto a enviar" }}

    3. "consultar_estado" (PREGUNTAS DEL TORNEO):
       - Frases: "¿Cuándo inicia?", "¿Cuánto vale?", "¿Premios?", "¿Qué hay de premios?", "Horarios".
       - JSON: {{ "intencion": "consultar_estado" }}

    4. "consulta_inscritos" (ESTADÍSTICAS):
       - Frases: "¿Cuántos inscritos hay?", "¿Cuánta gente va?", "Estadísticas".
       - JSON: {{ "intencion": "consulta_inscritos" }}

    5. "inscripcion":
       - Frases: "Quiero inscribirme", "Juego", "Soy Daniel".
       - JSON: {{ "intencion": "inscripcion", "nombre": "Nombre detectado" }}

    6. "reportar_victoria":
       - Frases: "Gané 3-0", "Victoria".
       - JSON: {{ "intencion": "reportar_victoria", "sets_ganador": 3, "sets_perdedor": 0 }}

    Si no es nada de esto, responde amable: {{ "intencion": "otra", "respuesta": "Soy Alejandro. Pregúntame por el torneo, inscripciones o resultados." }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": texto_usuario}],
            temperature=0
        )
        content = response.choices[0].message.content.replace("```json", "").replace("```", "")
        return json.loads(content)
    except:
        return {"intencion": "error"}