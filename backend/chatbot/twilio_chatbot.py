# filepath: twilio_chatbot.py
from flask import Flask, request, jsonify
from twilio.twiml import TwiMLMessagingResponse
from twilio.rest import Client
import random
import string
import os

app = Flask(__name__)

# Twilio credentials (set these in environment variables)
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'your_account_sid')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'your_auth_token')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', 'your_twilio_phone_number')

# Password generation function
def generate_password(length=16, upper=True, lower=True, numbers=True, symbols=True):
    chars = ''
    if upper: chars += string.ascii_uppercase
    if lower: chars += string.ascii_lowercase
    if numbers: chars += string.digits
    if symbols: chars += string.punctuation
    if not chars: chars = string.ascii_letters + string.digits
    
    password = ''.join(random.choices(chars, k=length))
    return password

# Help message
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

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Twilio messages"""
    incoming_msg = request.values.get('Body', '').strip().lower()
    sender = request.values.get('From', '')
    
    response = TwiMLMessagingResponse()
    
    # Parse command
    parts = incoming_msg.split()
    command = parts[0] if parts else 'help'
    
    try:
        if command == 'generate':
            # Default values
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
                    idx = parts.index(part)
                    if idx + 1 < len(parts):
                        val = parts[idx + 1].lower()
                        if val in ['no', 'false', 'off']:
                            if part == 'upper': upper = False
                            elif part == 'lower': lower = False
                            elif part == 'numbers': numbers = False
                            elif part == 'symbols': symbols = False
            
            password = generate_password(length, upper, lower, numbers, symbols)
            response.message(f"🔐 Your password ({length} chars):\n\n`{password}`\n\nCopy this carefully!")
            
        elif command == 'help':
            response.message(get_help_message())
            
        elif command == 'options':
            response.message("""⚙️ Password Options:
- upper: Uppercase letters (A-Z)
- lower: Lowercase letters (a-z)
- numbers: Numbers (0-9)
- symbols: Special characters (!@#$%^&*)

Example: generate 20 upper yes lower yes numbers no symbols yes""")
            
        else:
            response.message(f"Unknown command: {command}\n\n{get_help_message()}")
            
    except Exception as e:
        response.message(f"❌ Error: {str(e)}\n\n{get_help_message()}")
    
    return str(response)

@app.route('/test', methods=['GET'])
def test():
    """Test endpoint to generate password via web"""
    length = request.args.get('length', 16, type=int)
    password = generate_password(length)
    return jsonify({'password': password, 'length': length})

if __name__ == '__main__':
    # For local development, use ngrok to expose the webhook
    print("Starting Twilio Chatbot...")
    print("Use ngrok to expose this server to Twilio!")
    print(f"\nWebhook URL: ngrok_url/webhook")
    print("\nCommands:")
    print("  - generate - Generate default password")
    print("  - generate <length> - Generate with custom length")
    print("  - help - Show help message")
    app.run(debug=True, port=5001)