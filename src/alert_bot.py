import time
import os
import sys
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_loader import DataLoader
from src.regime_detector import RegimeDetector

# Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
CHECK_INTERVAL = 3600 # 1 Hour

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not found. Skipping alert.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Alert sent successfully.")
        else:
            print(f"Failed to send alert: {response.text}")
    except Exception as e:
        print(f"Error sending alert: {e}")

def get_market_status():
    loader = DataLoader(exchange_id='binance')
    # Fetch enough data for SMA 200
    df = loader.fetch_data('BTC/USDT', '1d', limit=210)
    
    if df is None:
        return None

    # Detect Regime
    detector = RegimeDetector(df)
    df = detector.detect_regime()
    regime = detector.get_current_regime()
    
    # Calculate Indicators
    df['sma_7'] = ta.sma(df['close'], length=7)
    df['sma_30'] = ta.sma(df['close'], length=30)
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Determine Action
    action = "WAIT"
    
    if regime['regime'] == 'Bull':
        if last['sma_7'] > last['sma_30']:
            action = "HOLD"
            if prev['sma_7'] <= prev['sma_30']:
                action = "BUY"
        else:
            action = "SELL" # Exit to cash in Bull pullback
            
    elif regime['regime'] == 'Sideways':
        # Bollinger logic
        bb = ta.bbands(df['close'], length=20, std=2.0)
        lower = bb[bb.columns[0]].iloc[-1]
        upper = bb[bb.columns[2]].iloc[-1]
        
        if last['close'] < lower:
            action = "BUY"
        elif last['close'] > upper:
            action = "SELL"
            
    elif regime['regime'] == 'Bear':
        action = "CASH"

    return {
        'price': last['close'],
        'regime': regime['regime'],
        'action': action,
        'sma_7': last['sma_7'],
        'sma_30': last['sma_30']
    }

def get_updates(offset=None):
    if not TELEGRAM_TOKEN:
        return []
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {'timeout': 10, 'offset': offset}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get('result', [])
    except Exception as e:
        print(f"Error getting updates: {e}")
    return []

def get_24h_summary():
    loader = DataLoader(exchange_id='binance')
    # Fetch 2 days of data to compare
    df = loader.fetch_data('BTC/USDT', '1d', limit=3)
    if df is None or len(df) < 2:
        return "No hay suficientes datos para el resumen."
        
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    change_pct = ((last['close'] - prev['close']) / prev['close']) * 100
    
    status = get_market_status()
    
    msg = (
        f"📊 **Resumen 24h**\n\n"
        f"**Precio**: ${last['close']:,.2f}\n"
        f"**Cambio 24h**: {change_pct:+.2f}%\n"
        f"**Régimen**: {status['regime']}\n"
        f"**Acción Sugerida**: {status['action']}\n"
        f"**SMA 7**: ${status['sma_7']:,.0f}\n"
        f"**SMA 30**: ${status['sma_30']:,.0f}"
    )
    return msg

def main():
    print("🤖 Alert Bot Started (Interactive)...")
    send_telegram_message("🤖 **Bot Actualizado**\n- Alerta diaria: 7:10 AM\n- Comando: /resumen disponible")
    
    last_action = None
    last_market_check = 0
    last_alive_day = None
    last_update_id = 0
    
    # Initial offset
    updates = get_updates()
    if updates:
        last_update_id = updates[-1]['update_id'] + 1
    
    while True:
        try:
            current_time = time.time()
            now = datetime.now()
            
            # 1. Check Market (Every Hour)
            if current_time - last_market_check > CHECK_INTERVAL:
                print(f"\nChecking market at {now}...")
                status = get_market_status()
                
                if status:
                    current_action = status['action']
                    # Alert on Change
                    if current_action != last_action:
                        emoji = "⚪"
                        if current_action == "BUY": emoji = "🟢"
                        elif current_action == "SELL": emoji = "🔴"
                        elif current_action == "CASH": emoji = "🛡️"
                        
                        msg = (
                            f"{emoji} **CAMBIO DE SEÑAL**\n\n"
                            f"**Acción**: {current_action}\n"
                            f"**Precio**: ${status['price']:,.2f}\n"
                            f"**Régimen**: {status['regime']}"
                        )
                        send_telegram_message(msg)
                        last_action = current_action
                
                last_market_check = current_time

            # 2. Daily Alive Message (7:10 AM)
            if now.hour == 7 and now.minute == 10 and last_alive_day != now.day:
                status = get_market_status()
                send_message_text = (
                    f"🌞 **Buenos días**\n\n"
                    f"**Estado del Mercado**:\n"
                    f"Precio: ${status['price']:,.2f}\n"
                    f"Régimen: {status['regime']}\n"
                    f"Acción: {status['action']}\n"
                    f"SMA 7: ${status['sma_7']:,.0f} | SMA 30: ${status['sma_30']:,.0f}"
                )
                send_telegram_message(send_message_text)
                last_alive_day = now.day
                
            # 3. Check Commands (Polling)
            updates = get_updates(offset=last_update_id)
            for update in updates:
                last_update_id = update['update_id'] + 1
                message = update.get('message', {})
                text = message.get('text', '')
                chat_id = message.get('chat', {}).get('id')
                
                # Security: Only respond to owner
                if str(chat_id) != str(TELEGRAM_CHAT_ID):
                    continue
                    
                if text == '/resumen':
                    print("Received /resumen command")
                    summary = get_24h_summary()
                    send_telegram_message(summary)
                    
            # Short sleep for polling loop
            time.sleep(5)
                
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
