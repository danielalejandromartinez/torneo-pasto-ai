from ai_agent import analizar_mensaje_ia

# Simulamos mensajes que llegarían por WhatsApp
mensajes_prueba = [
    "Hola, a que hora juego?",
    "Acabo de terminar, le gané a Carlos Crack 3 sets a 0, estuvo facil",
    "Gané 3-2 contra Luisa"
]

print("🧠 INICIANDO PRUEBA DE CEREBRO ARTIFICIAL...\n")

for mensaje in mensajes_prueba:
    print(f"📩 Mensaje recibido: {mensaje}")
    resultado = analizar_mensaje_ia(mensaje)
    print(f"📤 Lo que entendió la IA: {resultado}")
    print("-" * 30)