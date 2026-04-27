# Twilio Chatbot Setup Guide

## Prerequisites

1. **Twilio Account**: Sign up at https://www.twilio.com
2. **Twilio Phone Number**: Buy a phone number from Twilio Console
3. **ngrok** (for local development): Download from https://ngrok.com

## Installation

```bash
pip install -r requirements_chatbot.txt
```

## Configuration

### 1. Set Environment Variables

```bash
# Windows (Command Prompt)
set TWILIO_ACCOUNT_SID=your_account_sid
set TWILIO_AUTH_TOKEN=your_auth_token
set TWILIO_PHONE_NUMBER=+1xxxxxxxxxx

# Windows (PowerShell)
$env:TWILIO_ACCOUNT_SID="your_account_sid"
$env:TWILIO_AUTH_TOKEN="your_auth_token"
$env:TWILIO_PHONE_NUMBER="+1xxxxxxxxxx"
```

### 2. Get Your Twilio Credentials

1. Go to [Twilio Console](https://console.twilio.com)
2. Find **Account SID** and **Auth Token** in the dashboard
3. Buy a phone number from **Phone Numbers** → **Buy a Number**

## Running the Chatbot

### Option 1: Local Development with ngrok

1. Start the chatbot:
```bash
python twilio_chatbot.py
```

2. In another terminal, start ngrok:
```bash
ngrok http 5001
```

3. Copy the ngrok URL (e.g., `https://abc123.ngrok.io`)

### 2. Configure Twilio Webhook

1. Go to [Twilio Console](https://console.twilio.com) → **Phone Numbers**
2. Click on your purchased phone number
3. Under **Messaging** → **A message comes in**:
   - Select **Webhook**
   - Enter: `https://your-ngrok-url/webhook`
   - Set Method to **POST**
4. Click **Save**

## Testing

Send an SMS to your Twilio phone number:

| Command | Description |
|---------|-------------|
| `generate` | Generate 16-char password |
| `generate 20` | Generate 20-char password |
| `help` | Show help message |
| `options` | Show password options |

## Example Conversation

```
You: generate
Bot: 🔐 Your password (16 chars):

Xk9#mP2@nQ5vR8@L

Copy this carefully!

You: generate 12 upper yes lower no numbers yes symbols no
Bot: 🔐 Your password (12 chars):

847291035629

Copy this carefully!
```

## Deployment (Production)

For production, deploy to:
- **Render**: https://render.com
- **Railway**: https://railway.app
- **Heroku**: https://heroku.com

Update the webhook URL in Twilio Console to point to your deployed URL.