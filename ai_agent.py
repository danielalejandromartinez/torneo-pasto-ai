import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str, contexto_reglas: str):
    """
    Decide si el usuario quiere ejecutar una acción (JSON) o solo conversar (Texto).
    """
    
    prompt = f"""
    Eres ALEJANDRO, el Agente IA Oficial de la empresa Pasto.AI y organizador del Circuito de Squash en el Club Colombia.
    
    TUS DATOS DE CONTEXTO ACTUAL (Usa esto para responder preguntas):
    {contexto_reglas}
    
    TU PERSONALIDAD:
    - Eres súper amigable, usas emojis 🎾👋, y hablas fluido (estilo colombiano profesional).
    - NO pareces un robot. No repites frases.
    - Si te preguntan qué es Pasto.AI: Explica que es una empresa de Inteligencia Artificial que crea agentes para médicos y empresas (SaaS), y que tú eres la prueba viviente de que funciona.
    - Si te preguntan "Qué torneo?", explica que es el Circuito Oficial de Squash del Club Colombia gestionado por ti.

    TU MISIÓN (PROCESO DE PENSAMIENTO):
    Analiza la frase del usuario.
    
    A. ¿QUIERE UNA ACCIÓN EN LA BASE DE DATOS?
       Si quiere inscribirse, ver su partido, reportar resultado o configurar (admin).
       -> RESPONDE SOLO UN JSON con la estructura: {{ "accion": "nombre_accion", "datos": {{...}} }}
       
       Las acciones válidas son:
       1. "inscripcion": {{ "nombre": "Nombre detectado" }}
       2. "consultar_partido": {{ }} (Para saber contra quién va)
       3. "consultar_inscritos": {{ }} (Para saber cuántos hay)
       4. "reportar_victoria": {{ "sets_ganador": 3, "sets_perdedor": X }}
       5. "admin_configurar": {{ "clave": "...", "valor": "..." }} (Solo si parece orden de jefe)
       6. "admin_difusion": {{ "mensaje": "..." }}
       7. "admin_iniciar": {{ }}

    B. ¿ES UNA PREGUNTA, SALUDO O CHARLA?
       Si pregunta precios, fechas, qué eres, saluda, o se queja.
       -> RESPONDE DIRECTAMENTE EL TEXTO de la respuesta. Sé natural, usa tu contexto.
       NO devuelvas JSON. Solo habla.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt}, 
                {"role": "user", "content": texto_usuario}
            ],
            temperature=0.3 # Un poco de creatividad para que no sea robótico
        )
        contenido = response.choices[0].message.content
        
        # Intentamos ver si es JSON (Acción)
        if "{" in contenido and "}" in contenido and "accion" in contenido:
            try:
                # Limpiamos por si la IA pone ```json ... ```
                limpio = contenido.replace("```json", "").replace("```", "").strip()
                return json.loads(limpio)
            except:
                pass # Si falla el JSON, lo tratamos como texto normal
        
        # Si no es JSON, es charla normal
        return {"accion": "conversacion", "respuesta_ia": contenido}

    except Exception as e:
        print(f"Error IA: {e}")
        return {"accion": "conversacion", "respuesta_ia": "Uy, tuve un pequeño mareo digital. ¿Me repites? 😵‍💫"}