import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analizar_mensaje_ia(texto_usuario: str):
    prompt = """
    Eres Alejandro, el Agente IA de Pasto.AI.
    Tu misión es entender la INTENCIÓN del usuario en un torneo de Squash, aunque escriba informal o con errores.

    REGLAS DE INTERPRETACIÓN:

    1. INSCRIPCIÓN:
       Si el usuario manifiesta deseo de participar, jugar, entrar, anotarse.
       Busca nombres propios.
       Ejemplos: "Quiero jugar", "Me anoto soy Pedro", "Inscribirme", "Dale, yo juego".
       JSON: { "intencion": "inscripcion", "nombre": "Nombre detectado (Si no hay nombre explícito, usa 'Jugador')" }

    2. CONSULTA DE PARTIDO:
       Si pregunta por hora, rival, cuándo juega, programación.
       Ejemplos: "¿A qué hora me toca?", "¿Contra quién voy?", "Dime mi partido", "¿Cuándo juego?".
       JSON: { "intencion": "consultar_partido" }

    3. REPORTAR VICTORIA:
       Si dice que ganó, victoria, triunfo, o da un marcador favorable.
       Asume siempre que el que escribe es el ganador.
       Ejemplos: "Gané 3-0", "Le gané tres a uno", "Victoria 3-2", "Ganamos".
       JSON: { "intencion": "reportar_victoria", "sets_ganador": 3, "sets_perdedor": 0 }
       (Si no especifica marcador exacto pero dice que ganó, asume 3-0).

    4. INFORMACIÓN / CURIOSIDAD:
       Si pregunta qué eres, quién te hizo, info.
       JSON: { "intencion": "info_general" }

    Responde SOLO el JSON.
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