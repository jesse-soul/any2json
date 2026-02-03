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
  const { input, max_tokens = 500, type = 'auto' } = await request.json();
  
  // Get user for balance check
  const userData = await env.USERS.get(`user:${userId}`);
  const user = JSON.parse(userData);
  
  // TODO: Actual conversion logic with vision API
  // For now, mock response
  
  const result = {
    type: type === 'auto' ? 'image' : type,
    summary: `Processed: ${input.substring(0, 50)}...`,
    elements: [
      { id: 'e1', type: 'placeholder', content: 'Vision API integration pending' }
    ],
    metadata: {
      max_tokens,
      processed_at: new Date().toISOString(),
    },
    _expandable: ['e1'],
    _tokens_used: 75,
  };
  
  // Update usage
  const cost = 0.01; // $0.01 per request
  user.used += cost;
  await env.USERS.put(`user:${userId}`, JSON.stringify(user));
  
  return jsonResponse(result);
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
