/**
 * Cloudflare Worker for Croom Contact Form
 * Sends contact submissions to Telegram
 */

// CORS headers for the response
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

/**
 * Send message to Telegram
 * @param {string} botToken - Telegram Bot Token (from env)
 * @param {string} chatId - Telegram Chat ID (from env)
 * @param {string} message - Message to send
 * @returns {Promise<Response>}
 */
async function sendToTelegram(botToken, chatId, message) {
  const telegramUrl = `https://api.telegram.org/bot${botToken}/sendMessage`;

  const response = await fetch(telegramUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      chat_id: chatId,
      text: message,
      parse_mode: 'HTML',
      disable_web_page_preview: true,
    }),
  });

  return response;
}

/**
 * Format contact form data as Telegram message
 * @param {Object} data - Contact form data
 * @returns {string}
 */
function formatTelegramMessage(data) {
  const { name, email, subject, message, timestamp, userAgent } = data;

  return `
🔔 <b>New Contact Form Submission</b>

<b>From:</b> ${escapeHtml(name)}
<b>Email:</b> ${escapeHtml(email)}
<b>Subject:</b> ${escapeHtml(subject)}

<b>Message:</b>
${escapeHtml(message)}

───────────────────────
<b>Time:</b> ${new Date(timestamp).toUTCString()}
<b>User Agent:</b> ${escapeHtml(userAgent?.substring(0, 100) || 'Unknown')}
`.trim();
}

/**
 * Escape HTML special characters
 * @param {string} text
 * @returns {string}
 */
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text?.toString().replace(/[&<>"']/g, m => map[m]) || '';
}

/**
 * Validate contact form data
 * @param {Object} data
 * @returns {Object} { valid: boolean, error?: string }
 */
function validateContactData(data) {
  if (!data) {
    return { valid: false, error: 'No data provided' };
  }

  const { name, email, subject, message } = data;

  // Check required fields
  if (!name || name.trim().length === 0) {
    return { valid: false, error: 'Name is required' };
  }

  if (!email || email.trim().length === 0) {
    return { valid: false, error: 'Email is required' };
  }

  // Basic email validation
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    return { valid: false, error: 'Invalid email format' };
  }

  if (!subject || subject.trim().length === 0) {
    return { valid: false, error: 'Subject is required' };
  }

  if (!message || message.trim().length === 0) {
    return { valid: false, error: 'Message is required' };
  }

  // Check length limits
  if (name.length > 100) {
    return { valid: false, error: 'Name is too long (max 100 characters)' };
  }

  if (email.length > 100) {
    return { valid: false, error: 'Email is too long (max 100 characters)' };
  }

  if (subject.length > 200) {
    return { valid: false, error: 'Subject is too long (max 200 characters)' };
  }

  if (message.length > 5000) {
    return { valid: false, error: 'Message is too long (max 5000 characters)' };
  }

  return { valid: true };
}

/**
 * Handle OPTIONS request (CORS preflight)
 */
function handleOptions() {
  return new Response(null, {
    status: 204,
    headers: corsHeaders,
  });
}

/**
 * Handle POST request (contact form submission)
 */
async function handlePost(request, env) {
  try {
    // Parse JSON body
    let data;
    try {
      data = await request.json();
    } catch (e) {
      return new Response(JSON.stringify({
        success: false,
        message: 'Invalid JSON data'
      }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders,
        },
      });
    }

    // Validate data
    const validation = validateContactData(data);
    if (!validation.valid) {
      return new Response(JSON.stringify({
        success: false,
        message: validation.error
      }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders,
        },
      });
    }

    // Check if Telegram credentials are configured
    if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID) {
      console.error('Telegram credentials not configured');
      return new Response(JSON.stringify({
        success: false,
        message: 'Server configuration error'
      }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders,
        },
      });
    }

    // Send to Telegram
    const message = formatTelegramMessage(data);
    const telegramResponse = await sendToTelegram(
      env.TELEGRAM_BOT_TOKEN,
      env.TELEGRAM_CHAT_ID,
      message
    );

    if (!telegramResponse.ok) {
      const errorText = await telegramResponse.text();
      console.error('Telegram API error:', errorText);

      return new Response(JSON.stringify({
        success: false,
        message: 'Failed to send notification'
      }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders,
        },
      });
    }

    // Success response
    return new Response(JSON.stringify({
      success: true,
      message: 'Message sent successfully'
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders,
      },
    });

  } catch (error) {
    console.error('Error handling contact form:', error);

    return new Response(JSON.stringify({
      success: false,
      message: 'Internal server error'
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders,
      },
    });
  }
}

/**
 * Main worker entry point
 */
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Only allow /submit endpoint
    if (url.pathname !== '/submit') {
      return new Response('Not Found', {
        status: 404,
        headers: corsHeaders,
      });
    }

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return handleOptions();
    }

    // Handle POST request
    if (request.method === 'POST') {
      return handlePost(request, env);
    }

    // Method not allowed
    return new Response('Method Not Allowed', {
      status: 405,
      headers: corsHeaders,
    });
  },
};
