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
    return """🔐 *Password Generator Bot*

Welcome! You can generate a fully customized secure password step-by-step:

🚀 Reply with **`1`** (or type `generate`) to start the interactive custom builder!
🔄 Reply with **`0`** to regenerate a password using your last settings!

*💡 Tip:* You can skip the steps by typing a direct command, e.g.:
• `generate 20`
• `generate 12 upper no symbols`"""

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

    # Get or initialize session state
    if sender_id not in user_sessions:
        user_sessions[sender_id] = {
            'state': None,
            'length': 16,
            'upper': True,
            'lower': True,
            'numbers': True,
            'symbols': True
        }
    
    session = user_sessions[sender_id]
    state = session.get('state')

    # Allow escaping/resetting the wizard at any time
    if incoming_msg in ['menu', 'cancel', 'exit', 'reset', 'help']:
        session['state'] = None
        resp.message(get_help_message())
        return str(resp)

    # 1. State Machine Handling (Step-by-step wizard)
    if state == 'awaiting_length':
        try:
            val = int(incoming_msg)
            if 4 <= val <= 128:
                session['temp_length'] = val
                session['state'] = 'awaiting_uppercase'
                resp.message(
                    f"📏 Length set to *{val}*.\n\n"
                    f"*Step 2 of 5:* Include *Uppercase letters* (A-Z)?\n"
                    f"1️⃣ Yes\n"
                    f"2️⃣ No"
                )
            else:
                resp.message("⚠️ Please enter a number between 4 and 128.")
        except ValueError:
            resp.message("⚠️ Please enter a valid number, e.g., 16.")
        return str(resp)

    elif state == 'awaiting_uppercase':
        if incoming_msg in ['1', 'yes', 'y', 'true']:
            session['temp_upper'] = True
        elif incoming_msg in ['2', 'no', 'n', 'false']:
            session['temp_upper'] = False
        else:
            resp.message("⚠️ Please reply *1* (Yes) or *2* (No).")
            return str(resp)
        
        session['state'] = 'awaiting_lowercase'
        resp.message(
            f"*Step 3 of 5:* Include *Lowercase letters* (a-z)?\n"
            f"1️⃣ Yes\n"
            f"2️⃣ No"
        )
        return str(resp)

    elif state == 'awaiting_lowercase':
        if incoming_msg in ['1', 'yes', 'y', 'true']:
            session['temp_lower'] = True
        elif incoming_msg in ['2', 'no', 'n', 'false']:
            session['temp_lower'] = False
        else:
            resp.message("⚠️ Please reply *1* (Yes) or *2* (No).")
            return str(resp)
        
        session['state'] = 'awaiting_numbers'
        resp.message(
            f"*Step 4 of 5:* Include *Numbers* (0-9)?\n"
            f"1️⃣ Yes\n"
            f"2️⃣ No"
        )
        return str(resp)

    elif state == 'awaiting_numbers':
        if incoming_msg in ['1', 'yes', 'y', 'true']:
            session['temp_numbers'] = True
        elif incoming_msg in ['2', 'no', 'n', 'false']:
            session['temp_numbers'] = False
        else:
            resp.message("⚠️ Please reply *1* (Yes) or *2* (No).")
            return str(resp)
        
        session['state'] = 'awaiting_symbols'
        resp.message(
            f"*Step 5 of 5:* Include *Symbols* (!@#$)?\n"
            f"1️⃣ Yes\n"
            f"2️⃣ No"
        )
        return str(resp)

    elif state == 'awaiting_symbols':
        if incoming_msg in ['1', 'yes', 'y', 'true']:
            session['temp_symbols'] = True
        elif incoming_msg in ['2', 'no', 'n', 'false']:
            session['temp_symbols'] = False
        else:
            resp.message("⚠️ Please reply *1* (Yes) or *2* (No).")
            return str(resp)
        
        # We have all selections! Generate!
        session['state'] = None
        length = session['temp_length']
        upper = session['temp_upper']
        lower = session['temp_lower']
        numbers = session['temp_numbers']
        symbols = session['temp_symbols']
        
        # Save last successful settings (for regeneration)
        session['length'] = length
        session['upper'] = upper
        session['lower'] = lower
        session['numbers'] = numbers
        session['symbols'] = symbols
        
        try:
            pwd, _ = generate_password(length, upper, lower, numbers, symbols)
            emoji_strength = get_emoji_strength(length, upper, lower, numbers, symbols)
            
            response_text = (
                f"🎉 *Here is your customized password:*\n\n"
                f"`{pwd}`\n\n"
                f"📊 *Strength:* {emoji_strength} ({length} chars)\n\n"
                f"💡 _Tip: Reply *0* to instantly generate another password with these same settings, or reply *menu* to start fresh!_"
            )
            resp.message(response_text)
        except ValueError as e:
            resp.message(f"⚠️ Error: {str(e)}\nReply *menu* to start again.")
        return str(resp)

    # 2. Main Routing (When not in the middle of step-by-step wizard)
    parts = incoming_msg.split()
    command = parts[0] if parts else 'help'

    is_regenerate = False

    # Start the custom generation wizard
    if command in ['1', 'generate'] and len(parts) == 1:
        session['state'] = 'awaiting_length'
        resp.message(
            f"🚀 *Let's build your custom password!*\n\n"
            f"*Step 1 of 5:* Enter the desired *length* of your password (a number between 4 and 128):"
        )
        return str(resp)

    elif command in ['0', 'r', 'regenerate']:
        # Retrieve last session settings
        length = session.get('length', 16)
        upper = session.get('upper', True)
        lower = session.get('lower', True)
        numbers = session.get('numbers', True)
        symbols = session.get('symbols', True)
        is_regenerate = True
        command = 'generate_direct'

    elif command == 'generate':
        # Direct parsing if they entered parameters on a single line (e.g. generate 20)
        length = 16
        upper = True
        lower = True
        numbers = True
        symbols = True

        # Parse length
        if len(parts) > 1:
            try:
                length = int(parts[1])
                length = max(4, min(length, 128))
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
            session['length'] = length
            session['upper'] = upper
            session['lower'] = lower
            session['numbers'] = numbers
            session['symbols'] = symbols
            
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
            
    elif command in ['4', 'options']:
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
