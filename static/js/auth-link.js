/**
 * Shared Supabase auth-link handling for invite and password-reset pages.
 * Supports PKCE (?code=) and implicit (#access_token=) redirect formats.
 */
const FACEATTEND_SUPABASE_URL = 'https://xrlsltunfgjxooyyrora.supabase.co';
const FACEATTEND_SUPABASE_KEY = 'sb_publishable_qRH90RKcsglvtumJPWDxng_ju9Lploh';

function createFaceAttendAuthClient() {
  if (window.__faceattendSupabaseAuthClient) {
    return window.__faceattendSupabaseAuthClient;
  }

  const client = supabase.createClient(FACEATTEND_SUPABASE_URL, FACEATTEND_SUPABASE_KEY, {
    auth: {
      detectSessionInUrl: true,
      persistSession: true,
    },
  });

  window.__faceattendSupabaseAuthClient = client;
  return client;
}

function getHashParams() {
  const hash = window.location.hash.substring(1);
  if (!hash) return {};
  return Object.fromEntries(new URLSearchParams(hash));
}

function getQueryParams() {
  return Object.fromEntries(new URLSearchParams(window.location.search));
}

/**
 * Establish a session from the current URL (PKCE code or hash tokens).
 * @param {import('@supabase/supabase-js').SupabaseClient} client
 * @param {{ allowedTypes?: string[] }} options
 * @returns {Promise<{ ok: boolean, session?: object, error?: Error }>}
 */
async function establishSessionFromUrl(client, options = {}) {
  const allowedTypes = options.allowedTypes || ['invite', 'recovery', 'signup'];

  const { data: existing } = await client.auth.getSession();
  if (existing?.session) {
    return { ok: true, session: existing.session };
  }

  const query = getQueryParams();
  if (query.code) {
    const { data, error } = await client.auth.exchangeCodeForSession(query.code);
    if (error) return { ok: false, error };
    if (data?.session) return { ok: true, session: data.session };
    return { ok: false, error: new Error('No session returned from code exchange.') };
  }

  const hash = getHashParams();
  const accessToken = hash.access_token;
  const refreshToken = hash.refresh_token;
  const type = hash.type;

  if (!accessToken) {
    return { ok: false, error: new Error('No auth tokens found in this link.') };
  }

  if (type && !allowedTypes.includes(type)) {
    return { ok: false, error: new Error(`Unexpected link type: ${type}`) };
  }

  if (!refreshToken) {
    return { ok: false, error: new Error('Missing refresh token in link.') };
  }

  const { data, error } = await client.auth.setSession({
    access_token: accessToken,
    refresh_token: refreshToken,
  });
  if (error) return { ok: false, error };
  if (data?.session) return { ok: true, session: data.session };
  return { ok: false, error: new Error('Failed to establish session.') };
}
