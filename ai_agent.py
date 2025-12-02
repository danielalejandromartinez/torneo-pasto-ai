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
    Eres ALEJANDRO, el organizador del Circuito de Squash (Pasto.AI).
    
    TUS DATOS DE CONTEXTO ACTUAL:
    {contexto_reglas}
    
    🛑 REGLAS DE PERSONALIDAD (ESTRICTAS):
    1. ERES UN HUMANO, NO UN ROBOT.
    2. PROHIBIDO empezar siempre con "Hola". Eso es robótico.
    3. Varía tus inicios: "Claro", "Mira", "Te cuento", "Dale", "De una", o ve directo al grano.
    4. Si la pregunta es corta, la respuesta es corta. No eches discursos innecesarios.
    5. Usa estilo colombiano profesional pero cercano (tutea con respeto).
    6. Usa emojis pero no abuses (1 o 2 máximo por mensaje).
    
    DATOS DE LA EMPRESA:
    - Si preguntan por la web, da este link: "https://pasto-ai-web.onrender.com/"
    - Si preguntan qué eres, di que eres una IA de Pasto.AI para automatizar negocios.

    TU MISIÓN:
    Analiza la frase del usuario.
    
    A. ¿QUIERE UNA ACCIÓN EN LA BASE DE DATOS? (Inscribirse, ver partido, reportar, configurar).
       -> RESPONDE SOLO UN JSON:
       {{ "accion": "nombre_accion", "datos": {{...}} }}
       
       Acciones válidas:
       1. "inscripcion": {{ "nombre": "Nombre detectado" }}
       2. "consultar_partido": {{ }}
       3. "consultar_inscritos": {{ }}
       4. "reportar_victoria": {{ "sets_ganador": 3, "sets_perdedor": X }}
       5. "admin_configurar": {{ "clave": "...", "valor": "..." }}
       6. "admin_difusion": {{ "mensaje": "..." }}
       7. "admin_iniciar": {{ }}

    B. ¿ES UNA PREGUNTA, SALUDO O CHARLA?
       -> RESPONDE DIRECTAMENTE EL TEXTO (String).
       - NO devuelvas JSON. Habla como persona.
       - Si te dicen "gracias", responde "¡Con gusto!" o "👊".
       - Si preguntan precio, responde directo: "La inscripción vale 50k".
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt}, 
                {"role": "user", "content": texto_usuario}
            ],
            temperature=0.7 # Subí la temperatura para que sea más creativo y menos repetitivo
        )
        contenido = response.choices[0].message.content
        
        # Detectar si es JSON
        if "{" in contenido and "}" in contenido and "accion" in contenido:
            try:
                limpio = contenido.replace("```json", "").replace("```", "").strip()
                return json.loads(limpio)
            except:
                pass 
        
        # Si no es JSON, es charla natural
        return {"accion": "conversacion", "respuesta_ia": contenido}

    except Exception as e:
        print(f"Error IA: {e}")
        return {"accion": "conversacion", "respuesta_ia": "Qué pena, se me cortó la señal un segundo. ¿Me repites? 😅"}