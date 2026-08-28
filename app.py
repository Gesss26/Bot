from flask import Flask, request, jsonify
import requests
import json
import subprocess

app = Flask(__name__)
TOKEN = "7674593142:AAGhP_A5x9XIHQ1BKKufDA0jwjn2k2KerJg"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if data and 'message' in data:
            chat_id = data['message']['chat']['id']
            text = data['message'].get('text', '')
            
            # Gestisci i comandi qui
            if text == '/start':
                send_message(chat_id, "🤖 Bot attivo! Usa /start per iniziare")
            else:
                send_message(chat_id, "Usa /start per iniziare")
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error'}), 500

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': chat_id, 'text': text})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)