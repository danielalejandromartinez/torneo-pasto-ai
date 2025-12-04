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
    
    INSTRUCCIÓN: Responde SIEMPRE JSON.
    
    INTENCIONES:
    1. INSCRIPCIÓN:
       - "Inscribir a [Nombre]", "Quiero jugar".
       - JSON: {{ "accion": "inscripcion", "datos": {{ "nombre": "Nombre Detectado" }} }}
       *Si dice 'Quiero jugar' sin nombre, nombre = PERFIL_WHATSAPP*

    2. WIZARD ORGANIZADOR (PRIORIDAD ALTA):
       - Si el admin dice: "Organizar torneo", "Hacer cuadros", "Inicia torneo".
       - O si responde con datos cortos: "2", "30", "15:00", "Generar", "Cancelar".
       - JSON: {{ "accion": "admin_wizard", "datos": {{ "mensaje": "{texto_usuario}" }} }}

    3. REPORTAR VICTORIA:
       - "Gané 3-0", "Ganó Miguel".
       - JSON: {{ "accion": "ejecutar_victoria_ia", "datos": {{ ...datos del partido... }} }}

    4. CONSULTAS:
       - "¿Cuántos inscritos?", "Partidos". -> "consultar_inscritos", "consultar_partido".

    5. CHARLA / LINKS:
       - JSON: {{ "accion": "conversacion", "respuesta_ia": "..." }}
       - Web obligatoria en preguntas de "ver": https://torneo-pasto-ai.onrender.com/
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": texto_usuario}],
            temperature=0.2,
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"accion": "conversacion", "respuesta_ia": "Error."}