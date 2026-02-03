/**
 * any2json API — Cloudflare Worker
 * Handles auth, payments, and convert endpoints
 */

// KV Namespaces (bind in wrangler.toml):
// - USERS: user data
// - ADDRESSES: payment address pool
// - SESSIONS: auth sessions

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

// Simple JWT implementation for Edge
const JWT_SECRET = 'CHANGE_ME_IN_PRODUCTION'; // TODO: use env secret

async function hashPassword(password) {
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return btoa(String.fromCharCode(...new Uint8Array(hash)));
}

async function generateToken(userId) {
  const payload = {
    sub: userId,
    exp: Date.now() + (7 * 24 * 60 * 60 * 1000), // 7 days
  };
  // Simple encoding (in production use proper JWT)
  return btoa(JSON.stringify(payload));
}

async function verifyToken(token) {
  try {
    const payload = JSON.parse(atob(token));
    if (payload.exp < Date.now()) return null;
    return payload.sub;
  } catch {
    return null;
  }
}

function generateApiKey() {
  const bytes = new Uint8Array(24);
  crypto.getRandomValues(bytes);
  return 'a2j_' + Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
}

// Router
async function handleRequest(request, env) {
  const url = new URL(request.url);
  const path = url.pathname;
  
  // CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, { headers: CORS_HEADERS });
  }
  
  // Routes
  try {
    // Health check
    if (path === '/health') {
      return jsonResponse({ status: 'ok', version: '0.1.0', runtime: 'cloudflare-worker' });
    }
    
    // Auth routes
    if (path === '/api/auth/register' && request.method === 'POST') {
      return handleRegister(request, env);
    }
    
    if (path === '/api/auth/login' && request.method === 'POST') {
      return handleLogin(request, env);
    }
    
    // Protected routes
    const authHeader = request.headers.get('Authorization');
    const token = authHeader?.replace('Bearer ', '');
    const userId = token ? await verifyToken(token) : null;
    
    if (path === '/api/account/balance') {
      if (!userId) return jsonResponse({ error: 'Unauthorized' }, 401);
      return handleBalance(userId, env);
    }
    
    if (path === '/api/payments/get-address' && request.method === 'POST') {
      if (!userId) return jsonResponse({ error: 'Unauthorized' }, 401);
      return handleGetAddress(request, userId, env);
    }
    
    if (path === '/api/convert' && request.method === 'POST') {
      if (!userId) return jsonResponse({ error: 'Unauthorized' }, 401);
      return handleConvert(request, userId, env);
    }
    
    return jsonResponse({ error: 'Not found' }, 404);
    
  } catch (err) {
    return jsonResponse({ error: err.message }, 500);
  }
}

// Handlers
async function handleRegister(request, env) {
  const { email, password } = await request.json();
  
  if (!email || !password) {
    return jsonResponse({ error: 'Email and password required' }, 400);
  }
  
  // Check if exists
  const existing = await env.USERS.get(`email:${email}`);
  if (existing) {
    return jsonResponse({ error: 'Email already registered' }, 400);
  }
  
  const userId = crypto.randomUUID();
  const apiKey = generateApiKey();
  const passwordHash = await hashPassword(password);
  
  const user = {
    id: userId,
    email,
    passwordHash,
    apiKey,
    balance: 0,
    used: 0,
    tier: 'free',
    createdAt: Date.now(),
  };
  
  // Store user
  await env.USERS.put(`user:${userId}`, JSON.stringify(user));
  await env.USERS.put(`email:${email}`, userId);
  await env.USERS.put(`apikey:${apiKey}`, userId);
  
  const token = await generateToken(userId);
  
  return jsonResponse({ token, apiKey, userId });
}

async function handleLogin(request, env) {
  const { email, password } = await request.json();
  
  const userId = await env.USERS.get(`email:${email}`);
  if (!userId) {
    return jsonResponse({ error: 'Invalid credentials' }, 401);
  }
  
  const userData = await env.USERS.get(`user:${userId}`);
  const user = JSON.parse(userData);
  
  const passwordHash = await hashPassword(password);
  if (user.passwordHash !== passwordHash) {
    return jsonResponse({ error: 'Invalid credentials' }, 401);
  }
  
  const token = await generateToken(userId);
  
  return jsonResponse({ token, apiKey: user.apiKey });
}

async function handleBalance(userId, env) {
  const userData = await env.USERS.get(`user:${userId}`);
  if (!userData) {
    return jsonResponse({ error: 'User not found' }, 404);
  }
  
  const user = JSON.parse(userData);
  
  return jsonResponse({
    balance: user.balance,
    used: user.used,
    tier: user.tier,
  });
}

async function handleGetAddress(request, userId, env) {
  const { network } = await request.json();
  
  const networkNames = {
    trc20: 'USDT (TRC-20)',
    erc20: 'USDT (ERC-20)',
    dai: 'DAI (Ethereum)',
    xdai: 'xDAI (Gnosis)',
  };
  
  if (!networkNames[network]) {
    return jsonResponse({ error: 'Invalid network' }, 400);
  }
  
  // Check if user already has address
  const userAddrKey = `useraddr:${userId}:${network}`;
  const existingAddr = await env.ADDRESSES.get(userAddrKey);
  
  if (existingAddr) {
    return jsonResponse({
      address: existingAddr,
      network,
      networkName: networkNames[network],
    });
  }
  
  // Get next available address from pool
  const poolKey = `pool:${network}`;
  const pool = await env.ADDRESSES.get(poolKey);
  
  if (!pool) {
    return jsonResponse({ error: 'No addresses available' }, 503);
  }
  
  const addresses = JSON.parse(pool);
  if (addresses.length === 0) {
    return jsonResponse({ error: 'No addresses available' }, 503);
  }
  
  const address = addresses.shift();
  
  // Save updated pool and user assignment
  await env.ADDRESSES.put(poolKey, JSON.stringify(addresses));
  await env.ADDRESSES.put(userAddrKey, address);
  await env.ADDRESSES.put(`addr:${address}`, userId); // Reverse lookup
  
  return jsonResponse({
    address,
    network,
    networkName: networkNames[network],
  });
}

async function handleConvert(request, userId, env) {
  const { input, max_tokens = 500, type = 'auto', schema } = await request.json();
  
  if (!input) {
    return jsonResponse({ error: 'Input required (URL or base64)' }, 400);
  }
  
  // Get user for balance check
  const userData = await env.USERS.get(`user:${userId}`);
  const user = JSON.parse(userData);
  
  // Determine input type
  const isUrl = input.startsWith('http://') || input.startsWith('https://');
  const isBase64 = input.startsWith('data:') || /^[A-Za-z0-9+/=]+$/.test(input);
  
  if (!isUrl && !isBase64) {
    return jsonResponse({ error: 'Input must be URL or base64' }, 400);
  }
  
  // Prepare image for Vision API
  let imageContent;
  if (isUrl) {
    imageContent = { type: 'image_url', image_url: { url: input } };
  } else {
    // Handle base64
    const base64Data = input.startsWith('data:') ? input : `data:image/jpeg;base64,${input}`;
    imageContent = { type: 'image_url', image_url: { url: base64Data } };
  }
  
  // Build prompt based on max_tokens budget
  const detailLevel = max_tokens < 300 ? 'brief' : max_tokens < 1000 ? 'detailed' : 'comprehensive';
  
  const systemPrompt = `You are a vision-to-JSON converter. Extract structured data from images.
Output ONLY valid JSON, no markdown, no explanations.
Detail level: ${detailLevel} (budget: ~${max_tokens} tokens)

${schema ? `Use this schema: ${JSON.stringify(schema)}` : `Default schema:
{
  "type": "image",
  "summary": "brief description",
  "content": {
    "text": ["extracted text if any"],
    "objects": ["detected objects"],
    "scene": "scene description"
  },
  "metadata": {
    "dominant_colors": ["color1", "color2"],
    "style": "photo|illustration|screenshot|document|etc"
  }
}`}`;

  try {
    // Call OpenAI Vision API
    const openaiResponse = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${env.OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini', // Cost-effective vision model
        max_tokens: max_tokens,
        messages: [
          { role: 'system', content: systemPrompt },
          {
            role: 'user',
            content: [
              { type: 'text', text: 'Extract structured JSON from this image:' },
              imageContent
            ]
          }
        ],
        response_format: { type: 'json_object' }
      })
    });
    
    if (!openaiResponse.ok) {
      const error = await openaiResponse.text();
      console.error('OpenAI error:', error);
      return jsonResponse({ error: 'Vision API error', details: error }, 502);
    }
    
    const completion = await openaiResponse.json();
    const usage = completion.usage || {};
    
    // Parse the JSON response
    let result;
    try {
      result = JSON.parse(completion.choices[0].message.content);
    } catch {
      result = { raw: completion.choices[0].message.content };
    }
    
    // Calculate cost (GPT-4o-mini pricing: $0.15/1M input, $0.60/1M output)
    const inputCost = (usage.prompt_tokens || 0) * 0.00000015;
    const outputCost = (usage.completion_tokens || 0) * 0.0000006;
    const totalCost = inputCost + outputCost;
    
    // Add our margin (50%)
    const chargedCost = totalCost * 1.5;
    
    // Update usage
    user.used += chargedCost;
    await env.USERS.put(`user:${userId}`, JSON.stringify(user));
    
    return jsonResponse({
      ...result,
      _meta: {
        tokens_used: usage.total_tokens || 0,
        cost: chargedCost.toFixed(6),
        model: 'gpt-4o-mini',
        processed_at: new Date().toISOString(),
      }
    });
    
  } catch (err) {
    console.error('Convert error:', err);
    return jsonResponse({ error: 'Processing failed', details: err.message }, 500);
  }
}

// Helpers
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...CORS_HEADERS,
    },
  });
}

// Export
export default {
  async fetch(request, env, ctx) {
    return handleRequest(request, env);
  },
};
