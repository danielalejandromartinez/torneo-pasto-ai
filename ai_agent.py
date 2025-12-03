import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str, contexto_completo: str):
    """
    Agente Autónomo Gerencial.
    """
    
    prompt = f"""
    Eres ALEJANDRO, Gerente Deportivo de Pasto.AI.
    
    TU CONTEXTO ACTUAL (MEMORIA):
    {contexto_completo}
    
    TU MISIÓN: Gestionar el torneo de forma autónoma.
    
    INSTRUCCIONES DE RAZONAMIENTO (LOOP AUTÓNOMO):
    
    1. SI EL USUARIO ES ADMIN Y DICE "ORGANIZAR TORNEO" (O similar):
       - Revisa tu MEMORIA.
       - ¿Tienes configurado "num_canchas"?
       - ¿Tienes configurado "duracion_partido"?
       - ¿Tienes configurado "hora_inicio"?
       
       SI TE FALTA ALGO:
       - No intentes adivinar. Tu acción es PREGUNTARLE al admin.
       - JSON: {{ "accion": "conversacion", "respuesta_ia": "Jefe, para organizar necesito un dato: [Pregunta el dato que falta]" }}
       
       SI TIENES TODO:
       - Actúa como experto. Crea los emparejamientos (Round Robin o Llaves) y asigna horarios y canchas automáticamente.
       - JSON: {{ 
           "accion": "guardar_fixture_ia", 
           "datos": {{ 
               "partidos": [ 
                   {{"j1": "Nombre1", "j2": "Nombre2", "hora": "3:00 PM", "cancha": "1"}},
                   {{"j1": "Nombre3", "j2": "Nombre4", "hora": "3:00 PM", "cancha": "2"}}
                   ... (Todos los partidos necesarios)
               ] 
           }} 
         }}

    2. SI EL USUARIO RESPONDE UN DATO (Ej: "2 canchas", "30 minutos"):
       - Detecta qué dato es y guárdalo en configuración.
       - JSON: {{ "accion": "guardar_config", "datos": {{ "clave": "num_canchas (o el que corresponda)", "valor": "valor detectado" }} }}

    3. SI ES UNA ACCIÓN DE JUGADOR (Inscripción, Victoria, Consulta):
       - Aplica la lógica estándar.
       - "Inscribir a X" -> accion: inscripcion
       - "Gané" -> accion: reportar_victoria
       - "¿Contra quién voy?" -> accion: consultar_partido

    4. SI ES CHARLA GENERAL:
       - Responde amable y profesionalmente.
       - Web: https://pasto-ai-web.onrender.com/

    FORMATO JSON SIEMPRE.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt}, 
                {"role": "user", "content": texto_usuario}
            ],
            temperature=0.4, # Un poco de creatividad para organizar
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"accion": "conversacion", "respuesta_ia": "Error de proceso. 🤖"}