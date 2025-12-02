import requests
import time
import os
from dotenv import load_dotenv

# Load existing env to get token if present
load_dotenv()

def get_chat_id():
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        token = input("Ingresa tu Bot Token (el que te dio BotFather): ").strip()
    
    print(f"\n✅ Token: {token[:5]}...{token[-5:]}")
    print("\n👉 AHORA: Abre tu bot en Telegram y envíale un mensaje (ej: 'Hola').")
    print("⏳ Esperando mensaje...")

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    while True:
        try:
            response = requests.get(url)
            data = response.json()
            
            if data.get('ok'):
                results = data.get('result', [])
                if results:
                    # Get the last message
                    last_update = results[-1]
                    chat_id = last_update['message']['chat']['id']
                    user_name = last_update['message']['from'].get('first_name', 'Usuario')
                    
                    print(f"\n🎉 ¡Mensaje Recibido de {user_name}!")
                    print(f"🆔 TU CHAT ID ES: {chat_id}")
                    print("\n⚠️ Copia ese número y pégalo en tu archivo .env en TELEGRAM_CHAT_ID")
                    break
            
            time.sleep(2)
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    get_chat_id()
