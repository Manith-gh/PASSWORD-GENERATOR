import os
from flask import Flask, render_template, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import random
import string
import re

# Get the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(project_root, '..', '..', 'frontend'))

def generate_password(length, upper=True, lower=True, numbers=True, symbols=True):
    length = int(length)
    chars = ''
    if upper: chars += string.ascii_uppercase
    if lower: chars += string.ascii_lowercase
    if numbers: chars += string.digits
    if symbols: chars += string.punctuation
    if not chars:
        return jsonify({'error': 'Please select at least one character type!'}), 400
    password = ''.join(random.choices(chars, k=length))
    strength = 'weak' if length < 8 else 'moderate' if length < 16 else 'strong'
    return password, strength

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    pwd, strength = generate_password(
        data.get('length'),
        data.get('upper', True),
        data.get('lower', True),
        data.get('numbers', True),
        data.get('symbols', True)
    )
    return jsonify({'password': pwd, 'strength': strength})

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip().lower()
    resp = MessagingResponse()
    
    if incoming_msg.startswith('generate'):
        match = re.search(r'generate\s+(\d+)', incoming_msg)
        length = int(match.group(1)) if match else 16
        pwd, strength = generate_password(length=length)
        resp.message(f'Your {strength} password ({length} chars): `{pwd}`\nSend "generate [length]" for another.')
    else:
        resp.message('Send "generate [length]" (e.g., generate 20) for a password.')
    
    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)