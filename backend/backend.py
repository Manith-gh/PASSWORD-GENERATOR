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

# Global state to remember user's last generation settings for quick regeneration
user_sessions = {}

def get_emoji_strength(length, upper, lower, numbers, symbols):
    """Calculate and return a visual emoji strength indicator."""
    score = 0
    if length >= 8: score += 1
    if length >= 12: score += 1
    if length >= 16: score += 1
    
    types = sum([upper, lower, numbers, symbols])
    if types >= 3: score += 1
    if types == 4: score += 1
    
    if score <= 1:
        return "🔴🔴⚪⚪⚪ *Weak*"
    elif score <= 3:
        return "🟡🟡🟡⚪⚪ *Moderate*"
    elif score <= 4:
        return "🟢🟢🟢🟢⚪ *Strong*"
    else:
        return "🟢🟢🟢🟢🟢 *Extremely Strong!*"



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
    return """🔐 *Password Generator Menu*

Reply with a number for instant action:
1️⃣ *Generate* secure password (16 chars)
2️⃣ *Generate* short password (8 chars)
3️⃣ *Generate* long password (24 chars)
4️⃣ *Show advanced options & custom commands*

🔄 Reply with **`0`** at any time to regenerate a new password with your last settings!

*💡 Tip:* You can still type custom commands like `generate 20` or `generate 12 upper no symbols`!"""

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
    sender_id = request.values.get('From', 'default_user')
    resp = MessagingResponse()

    parts = incoming_msg.split()
    command = parts[0] if parts else 'help'

    # Map quick numeric shortcuts
    is_regenerate = False
    if command == '1':
        command = 'generate'
        parts = ['generate', '16']
    elif command == '2':
        command = 'generate'
        parts = ['generate', '8']
    elif command == '3':
        command = 'generate'
        parts = ['generate', '24']
    elif command == '4':
        command = 'help'
    elif command in ['0', 'r', 'regenerate']:
        # Retrieve last session settings if they exist
        if sender_id in user_sessions:
            session = user_sessions[sender_id]
            length = session['length']
            upper = session['upper']
            lower = session['lower']
            numbers = session['numbers']
            symbols = session['symbols']
            is_regenerate = True
            command = 'generate_direct'
        else:
            # Fallback to default generate if no previous session
            command = 'generate'
            parts = ['generate', '16']

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
        command = 'generate_direct'

    if command == 'generate_direct':
        try:
            pwd, _ = generate_password(length, upper, lower, numbers, symbols)
            
            # Save settings in session
            user_sessions[sender_id] = {
                'length': length,
                'upper': upper,
                'lower': lower,
                'numbers': numbers,
                'symbols': symbols
            }
            
            # Build interactive response
            emoji_strength = get_emoji_strength(length, upper, lower, numbers, symbols)
            prefix = "🔄 *Regenerated password using your last settings:*\n\n" if is_regenerate else "🔐 *Your secure password:*\n\n"
            
            response_text = (
                f"{prefix}`{pwd}`\n\n"
                f"📊 *Strength:* {emoji_strength} ({length} chars)\n\n"
                f"💡 _Tip: Reply *0* to instantly generate another password with these same settings!_"
            )
            resp.message(response_text)
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
