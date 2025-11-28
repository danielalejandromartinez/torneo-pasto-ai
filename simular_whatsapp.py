import requests
import time

# La dirección de tu servidor local
URL_WEBHOOK = "http://127.0.0.1:8000/webhook"

def enviar_mensaje_falso(mensaje, usuario):
    payload = {
        "mensaje": mensaje,
        "usuario": usuario
    }
    print(f"📱 Enviando WhatsApp simulado: '{mensaje}'...")
    
    try:
        respuesta = requests.post(URL_WEBHOOK, json=payload)
        if respuesta.status_code == 200:
            print(f"🤖 El Bot respondió: {respuesta.json()['respuesta_bot']}")
        else:
            print(f"⚠️ Error del servidor: {respuesta.status_code}")
    except Exception as e:
        print(f"❌ Error: El servidor parece apagado. {e}")

# --- ESCENARIO DE PRUEBA ---

print("--- INICIANDO SIMULACIÓN ---")

# 1. Alguien pregunta algo random (para calentar motores)
enviar_mensaje_falso("Hola, a que hora juego?", "Carlos Crack")
print("-" * 20)
time.sleep(2)

# 2. Carlos Crack reporta una victoria real contra Luisa Volea
# Usamos "Parce" para probar que la IA ya es inteligente y lo ignora
enviar_mensaje_falso("Parce, le gané a Luisa Volea 3 sets a 0, estuvo facil", "Carlos Crack")