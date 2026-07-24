import quizData from './阶段A_题库与报告_v1.0.json' with { type: 'json' };

const encoder = new TextEncoder();
const SESSION_DAYS = 30;

function json(payload, status = 200, headers = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'private, no-store', ...headers }
  });
}

function normalizeCode(value) {
  return String(value || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
}

function base64url(bytes) {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function decodeBase64url(value) {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  const binary = atob(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '='));
  return Uint8Array.from(binary, char => char.charCodeAt(0));
}

async function sha256(value) {
  return base64url(new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(value))));
}

async function hmac(secret, value) {
  const key = await crypto.subtle.importKey('raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return base64url(new Uint8Array(await crypto.subtle.sign('HMAC', key, encoder.encode(value))));
}

async function makeSession(env, claims) {
  const payload = base64url(encoder.encode(JSON.stringify({ ...claims, exp: Date.now() + SESSION_DAYS * 86400000 })));
  return `${payload}.${await hmac(env.SESSION_SECRET, payload)}`;
}

async function readSession(request, env) {
  const cookie = request.headers.get('Cookie') || '';
  const match = cookie.match(/(?:^|;\s*)re_session=([^;]+)/);
  if (!match || !env.SESSION_SECRET) return null;
  const [payload, signature] = match[1].split('.');
  if (!payload || !signature || await hmac(env.SESSION_SECRET, payload) !== signature) return null;
  try {
    const claims = JSON.parse(new TextDecoder().decode(decodeBase64url(payload)));
    return claims.exp > Date.now() ? claims : null;
  } catch (_) {
    return null;
  }
}

function sessionCookie(token) {
  return `re_session=${token}; Path=/; Max-Age=${SESSION_DAYS * 86400}; HttpOnly; Secure; SameSite=Strict`;
}

function randomCode() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  const raw = Array.from(bytes, byte => alphabet[byte % alphabet.length]).join('');
  return `RE-${raw.slice(0, 4)}-${raw.slice(4, 8)}-${raw.slice(8, 12)}-${raw.slice(12)}`;
}

async function unlock(request, env) {
  if (!env.DB || !env.SESSION_SECRET) return json({ message: '服务尚未完成配置。' }, 503);
  const body = await request.json().catch(() => ({}));
  const code = normalizeCode(body.code);
  const deviceId = String(body.deviceId || '').trim();
  if (code.length < 12 || deviceId.length < 16 || deviceId.length > 128) return json({ message: '兑换码格式不正确。' }, 400);

  const codeHash = await sha256(code);
  const deviceHash = await sha256(deviceId);
  const record = await env.DB.prepare(
    `SELECT id, max_devices AS maxDevices, expires_at AS expiresAt
     FROM access_codes WHERE code_hash = ? AND active = 1`
  ).bind(codeHash).first();
  if (!record || (record.expiresAt && Date.parse(record.expiresAt) < Date.now())) return json({ message: '兑换码无效或已过期，请检查后重试。' }, 403);

  const existing = await env.DB.prepare('SELECT 1 FROM code_devices WHERE code_id = ? AND device_hash = ?')
    .bind(record.id, deviceHash).first();
  if (!existing) {
    const count = await env.DB.prepare('SELECT COUNT(*) AS total FROM code_devices WHERE code_id = ?').bind(record.id).first();
    if (Number(count.total) >= Number(record.maxDevices)) return json({ message: '这枚兑换码已达到可用设备数量。如需更换设备，请联系卖家。' }, 403);
    await env.DB.batch([
      env.DB.prepare('INSERT OR IGNORE INTO code_devices (code_id, device_hash) VALUES (?, ?)').bind(record.id, deviceHash),
      env.DB.prepare('UPDATE access_codes SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?').bind(record.id)
    ]);
  }

  const token = await makeSession(env, { codeId: record.id, deviceHash, preview: false });
  return json({ authorized: true }, 200, { 'Set-Cookie': sessionCookie(token) });
}

async function session(request, env, url) {
  const preview = url.searchParams.get('preview');
  if (preview) {
    if (!env.PREVIEW_KEY || preview !== env.PREVIEW_KEY) return json({ authorized: false }, 403);
    const token = await makeSession(env, { preview: true });
    return json({ authorized: true, preview: true }, 200, { 'Set-Cookie': sessionCookie(token) });
  }
  const claims = await readSession(request, env);
  return json({ authorized: Boolean(claims), preview: Boolean(claims?.preview) }, claims ? 200 : 401);
}

async function serveQuizData(request, env) {
  const claims = await readSession(request, env);
  if (!claims) return json({ message: '请先使用兑换码解锁。' }, 401);
  if (claims.preview) return json(quizData);
  const { testPresets: _internalPresets, ...publicQuizData } = quizData;
  return json(publicQuizData);
}

async function createCodes(request, env) {
  const authorization = request.headers.get('Authorization');
  if (!env.ADMIN_SECRET || authorization !== `Bearer ${env.ADMIN_SECRET}`) return json({ message: '无权执行此操作。' }, 401);
  if (!env.DB) return json({ message: '数据库尚未配置。' }, 503);
  const body = await request.json().catch(() => ({}));
  const count = Math.min(Math.max(Number(body.count) || 1, 1), 100);
  const maxDevices = Math.min(Math.max(Number(body.maxDevices) || 2, 1), 5);
  const batch = String(body.batch || 'manual').slice(0, 80);
  const expiresAt = body.expiresAt ? new Date(body.expiresAt).toISOString() : null;
  const codes = Array.from({ length: count }, randomCode);
  const statements = await Promise.all(codes.map(async code => env.DB.prepare(
    'INSERT INTO access_codes (code_hash, max_devices, batch, expires_at) VALUES (?, ?, ?, ?)'
  ).bind(await sha256(normalizeCode(code)), maxDevices, batch, expiresAt)));
  await env.DB.batch(statements);
  return json({ codes, maxDevices, batch, expiresAt });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/api/unlock' && request.method === 'POST') return unlock(request, env);
    if (url.pathname === '/api/session' && request.method === 'GET') return session(request, env, url);
    if (url.pathname === '/api/quiz-data' && request.method === 'GET') return serveQuizData(request, env);
    if (url.pathname === '/api/admin/codes' && request.method === 'POST') return createCodes(request, env);
    if (url.pathname.startsWith('/api/')) return json({ message: '接口不存在。' }, 404);
    if (url.pathname.endsWith('.json') || url.pathname.endsWith('.py') || url.pathname.endsWith('.md')) return new Response('Not found', { status: 404 });
    return env.ASSETS.fetch(request);
  }
};
