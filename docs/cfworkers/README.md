# Croom Contact Form - Cloudflare Worker

This Cloudflare Worker handles contact form submissions from the Croom website and sends notifications to Telegram.

## Features

- ✅ Validates all form inputs
- ✅ Sends formatted notifications to Telegram
- ✅ CORS-enabled for cross-origin requests
- ✅ Rate limiting ready (can be added)
- ✅ Secure credential management via Cloudflare secrets
- ✅ HTML escaping for security

## Setup Instructions

### 1. Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the instructions
3. Save the **Bot Token** (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Send a message to your bot to start it

### 2. Get Your Chat ID

1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"chat":{"id":123456789}` in the response
4. Save the **Chat ID** (it's a number, can be negative for groups)

Alternatively, you can:
- Add [@userinfobot](https://t.me/userinfobot) to get your personal chat ID
- Add your bot to a group and use [@getidsbot](https://t.me/getidsbot) to get the group chat ID

### 3. Install Wrangler CLI

```bash
npm install -g wrangler
# or
pnpm add -g wrangler
```

### 4. Login to Cloudflare

```bash
wrangler login
```

### 5. Deploy the Worker

```bash
cd docs/cfworkers
wrangler deploy
```

### 6. Set Secrets

Set your Telegram credentials as secrets (never commit these!):

```bash
# Set the Bot Token
wrangler secret put TELEGRAM_BOT_TOKEN
# When prompted, paste your bot token

# Set the Chat ID
wrangler secret put TELEGRAM_CHAT_ID
# When prompted, paste your chat ID
```

### 7. Configure Custom Domain (Optional)

#### Option A: Via Cloudflare Dashboard

1. Go to your Cloudflare Dashboard
2. Navigate to Workers & Pages → your worker
3. Go to Settings → Triggers
4. Add a Custom Domain: `contact.croom.to`

#### Option B: Via wrangler.toml

Uncomment and update the routes in `wrangler.toml`:

```toml
routes = [
  { pattern = "contact.croom.to/*", zone_name = "croom.to" }
]
```

Then redeploy:

```bash
wrangler deploy
```

### 8. Update Website Configuration

Update the contact form endpoint in `docs/contact/index.html`:

```javascript
const WORKER_URL = 'https://contact.croom.to/submit';
```

Or use the workers.dev URL during development:

```javascript
const WORKER_URL = 'https://croom-contact-handler.<your-account>.workers.dev/submit';
```

## Testing

### Test with curl

```bash
curl -X POST https://contact.croom.to/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Test Subject",
    "message": "This is a test message",
    "timestamp": "2024-01-01T00:00:00Z",
    "userAgent": "Test Agent"
  }'
```

### Expected Response

Success:
```json
{
  "success": true,
  "message": "Message sent successfully"
}
```

Error:
```json
{
  "success": false,
  "message": "Error description"
}
```

## Telegram Message Format

You'll receive messages in this format:

```
🔔 New Contact Form Submission

From: John Doe
Email: john@example.com
Subject: Question about pricing

Message:
Hello, I have a question about your pricing...

───────────────────────
Time: Mon, 01 Jan 2024 12:00:00 GMT
User Agent: Mozilla/5.0...
```

## Security Features

- **Input Validation**: All fields are validated for presence, format, and length
- **HTML Escaping**: All user input is escaped before sending to Telegram
- **CORS Protection**: Only allows POST and OPTIONS methods
- **Length Limits**:
  - Name: 100 characters
  - Email: 100 characters
  - Subject: 200 characters
  - Message: 5000 characters
- **Email Format Validation**: Basic regex validation
- **Secret Management**: Credentials stored as Cloudflare secrets, never in code

## Rate Limiting (Optional)

To add rate limiting, you can use Cloudflare's Rate Limiting or add custom logic:

```javascript
// In the worker code
const RATE_LIMIT = 5; // 5 submissions per IP per hour
const RATE_WINDOW = 3600; // 1 hour in seconds

// Use KV or Durable Objects to track submissions per IP
```

## Monitoring

View worker logs:

```bash
wrangler tail
```

Or check the Cloudflare Dashboard:
- Workers & Pages → your worker → Logs

## Updating the Worker

After making changes to `contact-handler.js`:

```bash
wrangler deploy
```

## Environment Variables

The worker uses these secrets (set via `wrangler secret put`):

| Secret | Description | Example |
|--------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram Bot Token | `123456789:ABCdef...` |
| `TELEGRAM_CHAT_ID` | Your Telegram Chat ID | `123456789` |

## Troubleshooting

### "Server configuration error"

- Make sure you've set both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` secrets
- Verify secrets are set: `wrangler secret list`

### "Failed to send notification"

- Check if the bot token is correct
- Verify the chat ID is correct
- Make sure you've sent at least one message to the bot
- Check worker logs: `wrangler tail`

### CORS errors

- Verify the worker URL is correct in your contact form
- Check browser console for detailed error messages

### Messages not arriving

- Send a test message directly to your bot to verify it's working
- Check the chat ID is correct (use `/getUpdates` endpoint)
- Review worker logs for errors

## Development

To test locally with Wrangler:

```bash
wrangler dev
```

This will start a local server at `http://localhost:8787`

## Cost

Cloudflare Workers Free Tier includes:
- 100,000 requests per day
- 10ms CPU time per request

This should be more than enough for a contact form!

## Links

- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/)
