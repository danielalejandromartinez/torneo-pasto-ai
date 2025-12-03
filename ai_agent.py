import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str, contexto_completo: str):
    prompt = f"""
    Eres ALEJANDRO, el Gerente Deportivo Autónomo de Pasto.AI.
    
    TU CONTEXTO REAL (MEMORIA DE BASE DE DATOS):
    {contexto_completo}
    
    TU MISIÓN:
    Ser un organizador experto. No esperes instrucciones paso a paso.
    Si el usuario dice "Organiza el torneo", "Haz los cuadros", "Programa los partidos":
    1. Mira la lista de JUGADORES INSCRITOS en tu contexto.
    2. Usa tu inteligencia para crear los emparejamientos (Round Robin, Eliminación, lo que veas mejor según la cantidad).
    3. Asigna horarios lógicos (ej: cada 30 mins) y canchas (1 y 2).
    4. Genera la acción "guardar_organizacion_ia" con la lista de partidos.

    ESTRUCTURA DE RESPUESTA JSON (SIEMPRE):
    {{
        "accion": "nombre_accion",
        "datos": {{ ... }},
        "respuesta_ia": "Texto amable explicando qué hiciste"
    }}

    ACCIONES POSIBLES:
    
    1. ORGANIZAR TORNEO (AUTÓNOMO):
       - JSON: 
         {{
           "accion": "guardar_organizacion_ia",
           "datos": {{
             "partidos": [
                {{ "j1_nombre": "Juan", "j2_nombre": "Pedro", "hora": "3:00 PM", "cancha": "1" }},
                {{ "j1_nombre": "Ana", "j2_nombre": "Maria", "hora": "3:30 PM", "cancha": "1" }}
                ... (Todos los partidos necesarios)
             ]
           }},
           "respuesta_ia": "¡Listo! He analizado los inscritos y he creado el fixture perfecto. Revisa la programación."
         }}

    2. INSCRIPCIÓN:
       - "Inscribir a [Nombre]".
       - JSON: {{ "accion": "inscripcion", "datos": {{ "nombre": "Nombre Detectado" }} }}

    3. REPORTAR VICTORIA:
       - "Gané 3-0", "Ganó Miguel".
       - JSON: {{ "accion": "reportar_victoria", "datos": {{ "sets_ganador": 3, "sets_perdedor": 0, "nombre_ganador": "Nombre Detectado (opcional)" }} }}

    4. CONSULTAS:
       - "¿Contra quién juego?", "¿Cuántos hay?".
       - Acciones: "consultar_partido", "consultar_inscritos".

    5. CHARLA:
       - JSON: {{ "accion": "conversacion", "respuesta_ia": "..." }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt}, 
                {"role": "user", "content": texto_usuario}
            ],
            temperature=0.3, 
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"accion": "conversacion", "respuesta_ia": "Error de proceso. 🤖"}