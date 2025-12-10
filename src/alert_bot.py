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

# Assets to Monitor
MONITORED_ASSETS = [
    {'type': 'crypto', 'symbol': 'BTC/USDT', 'name': 'Bitcoin'},
    {'type': 'fintual', 'id': 186, 'name': 'Risky Norris'},
    {'type': 'fintual', 'id': 187, 'name': 'Moderate Pitt'}
]

def get_market_status(asset):
    loader = DataLoader(exchange_id='binance')
    timeframe = '1d'
    
    if asset['type'] == 'crypto':
        df = loader.fetch_data(asset['symbol'], timeframe, limit=210)
    else:
        df = loader.fetch_fintual_data(asset['id'], limit=210)
        
    if df is None or df.empty:
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
            action = "SELL" 
            
    elif regime['regime'] == 'Sideways':
        bb = ta.bbands(df['close'], length=20, std=2.0)
        # Check if BB columns exist (might fail on short data)
        if bb is not None and len(bb.columns) >= 3:
            lower = bb[bb.columns[0]].iloc[-1]
            upper = bb[bb.columns[2]].iloc[-1]
            
            if last['close'] < lower:
                action = "BUY"
            elif last['close'] > upper:
                action = "SELL"
            
    elif regime['regime'] == 'Bear':
        action = "CASH"

    return {
        'name': asset['name'],
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

def get_full_summary():
    msg = "📊 **Resumen de Mercado**\n\n"
    
    for asset in MONITORED_ASSETS:
        status = get_market_status(asset)
        if status:
            msg += (
                f"🔹 **{status['name']}**\n"
                f"Precio: ${status['price']:,.2f}\n"
                f"Régimen: {status['regime']}\n"
                f"Acción: {status['action']}\n"
                f"SMA 7/30: ${status['sma_7']:,.0f} / ${status['sma_30']:,.0f}\n\n"
            )
        else:
            msg += f"🔹 **{asset['name']}**: Error fetching data.\n\n"
            
    return msg

def main():
    print("🤖 Alert Bot Started (Multi-Asset)...")
    send_telegram_message("🤖 **Bot Actualizado**\nMonitoreando Bitcoin + Fintual.")
    
    # Store last action per asset name
    last_actions = {} 
    
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
                
                for asset in MONITORED_ASSETS:
                    status = get_market_status(asset)
                    if status:
                        name = status['name']
                        action = status['action']
                        
                        # Initialize last action if new
                        if name not in last_actions:
                            last_actions[name] = None
                            
                        # Alert on Change
                        if action != last_actions[name]:
                            emoji = "⚪"
                            if action == "BUY": emoji = "🟢"
                            elif action == "SELL": emoji = "🔴"
                            elif action == "CASH": emoji = "🛡️"
                            
                            msg = (
                                f"{emoji} **CAMBIO EN {name.upper()}**\n\n"
                                f"**Acción**: {action}\n"
                                f"**Precio**: ${status['price']:,.2f}\n"
                                f"**Régimen**: {status['regime']}"
                            )
                            send_telegram_message(msg)
                            last_actions[name] = action
                        
                        print(f"{name}: {action} | {status['regime']}")
                
                last_market_check = current_time

            # 2. Daily Alive Message (7:10 AM)
            if now.hour == 7 and now.minute == 10 and last_alive_day != now.day:
                summary = get_full_summary()
                msg = f"🌞 **Buenos días**\n\n{summary}"
                send_telegram_message(msg)
                last_alive_day = now.day
                
            # 3. Check Commands (Polling)
            updates = get_updates(offset=last_update_id)
            for update in updates:
                last_update_id = update['update_id'] + 1
                message = update.get('message', {})
                text = message.get('text', '')
                chat_id = message.get('chat', {}).get('id')
                
                if str(chat_id) != str(TELEGRAM_CHAT_ID):
                    continue
                    
                if text == '/resumen':
                    print("Received /resumen command")
                    summary = get_full_summary()
                    send_telegram_message(summary)
                    
            time.sleep(5)
                
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
