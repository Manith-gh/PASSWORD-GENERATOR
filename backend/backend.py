import os
import random
import string
import re
from flask import Flask, render_template, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

# Get the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))
# frontend is located at root level (../frontend)
app = Flask(__name__, template_folder=os.path.join(project_root, '..', 'frontend'))

# Twilio credentials (set these in environment variables)
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

# Optional Twilio client initialization
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    except Exception as e:
        app.logger.warning(f"Twilio Client initialization failed: {e}")

def generate_password(length, upper=True, lower=True, numbers=True, symbols=True):
    """Consolidated password generator with input validation."""
    try:
        length = int(length)
    except (ValueError, TypeError):
        length = 16

    # Clamp length between 4 and 128
    length = max(4, min(length, 128))

    chars = ''
    if upper: chars += string.ascii_uppercase
    if lower: chars += string.ascii_lowercase
    if numbers: chars += string.digits
    if symbols: chars += string.punctuation

    if not chars:
        raise ValueError("Please select at least one character type!")

    password = ''.join(random.choices(chars, k=length))
    strength = 'weak' if length < 8 else 'moderate' if length < 16 else 'strong'
    return password, strength

def get_help_message():
    return """🔐 Password Generator Bot

Commands:
- generate <length> - Generate a password (default: 16 chars)
- help - Show this help message
- options - Show password options

Examples:
- generate
- generate 20
- generate 12 upper no symbols

Available options: upper, lower, numbers, symbols
Use yes/no or true/false to toggle options."""

def get_options_message():
    return """⚙️ Password Options:
- upper: Uppercase letters (A-Z)
- lower: Lowercase letters (a-z)
- numbers: Numbers (0-9)
- symbols: Special characters (!@#$%^&*)

Example: generate 20 upper yes lower yes numbers no symbols yes"""

# ----------------- GLOBAL CRASH ISOLATION SHIELD -----------------
@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler to isolate failures between website and chatbot routes."""
    app.logger.error(f"Unhandled Exception on {request.path}: {str(e)}", exc_info=True)

    # Twilio Webhook Endpoints
    if request.path in ['/webhook', '/whatsapp']:
        resp = MessagingResponse()
        resp.message("⚠️ The chatbot encountered an unexpected error. Please try again.")
        return str(resp), 200

    # API Endpoints
    if request.path.startswith('/api/'):
        return jsonify({'error': 'An internal server error occurred.'}), 500

    # Fallback/HTML Page views
    return "An internal server error occurred.", 500


# ----------------- WEBSITE ROUTES -----------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json or {}
    try:
        pwd, strength = generate_password(
            data.get('length', 8),
            data.get('upper', True),
            data.get('lower', True),
            data.get('numbers', True),
            data.get('symbols', True)
        )
        return jsonify({'password': pwd, 'strength': strength})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ----------------- TWILIO CHATBOT WEBHOOKS -----------------
@app.route('/webhook', methods=['POST'])
@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip().lower()
    resp = MessagingResponse()

    parts = incoming_msg.split()
    command = parts[0] if parts else 'help'

    if command == 'generate':
        length = 16
        upper = True
        lower = True
        numbers = True
        symbols = True

        # Parse length
        if len(parts) > 1:
            try:
                length = int(parts[1])
                length = max(6, min(length, 64))  # Clamp between 6-64
            except ValueError:
                pass

        # Parse options
        for part in parts[2:]:
            if part in ['upper', 'lower', 'numbers', 'symbols']:
                try:
                    idx = parts.index(part)
                    if idx + 1 < len(parts):
                        val = parts[idx + 1].lower()
                        if val in ['no', 'false', 'off']:
                            if part == 'upper': upper = False
                            elif part == 'lower': lower = False
                            elif part == 'numbers': numbers = False
                            elif part == 'symbols': symbols = False
                except ValueError:
                    pass

        try:
            pwd, strength = generate_password(length, upper, lower, numbers, symbols)
            resp.message(f"🔐 Your {strength} password ({length} chars):\n\n`{pwd}`\n\nCopy this carefully!")
        except ValueError as e:
            resp.message(f"⚠️ Error: {str(e)}\nUse 'options' command to see available parameters.")
            
    elif command == 'help':
        resp.message(get_help_message())

    elif command == 'options':
        resp.message(get_options_message())

    else:
        resp.message(f"Unknown command: {command}\n\n{get_help_message()}")

    return str(resp)


@app.route('/api/test', methods=['GET'])
@app.route('/test', methods=['GET'])
def test():
    """Test endpoint to generate password via GET request"""
    length = request.args.get('length', 16, type=int)
    try:
        password, strength = generate_password(length)
        return jsonify({'password': password, 'length': length, 'strength': strength})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting combined server on port {port}...")
    app.run(debug=True, host='0.0.0.0', port=port)
