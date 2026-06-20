if (typeof supabase === 'undefined') {
  document.getElementById('login-screen').innerHTML = `
    <div class="login-card">
      <div class="logo">Face<span>Attend</span></div>
      <div class="error-msg" style="display:block;margin-top:16px;">
        Failed to load. Check your internet connection and refresh.
      </div>
    </div>`;
  throw new Error('Supabase SDK failed to load');
}

const SUPABASE_URL      = "https://xrlsltunfgjxooyyrora.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_qRH90RKcsglvtumJPWDxng_ju9Lploh";
function faceattendApiBase() {
  if (typeof location === "undefined") return "https://faceattend.app";
  const host = location.hostname;
  if (host === "faceattend.app" || host.endsWith(".faceattend.app")) {
    return `${location.protocol}//${location.host}`;
  }
  return "https://faceattend.app";
}
const API_URL = faceattendApiBase();
const DAZZLING_URL = API_URL;

const { createClient } = supabase;
const client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// ── Sign out helper ────────────────────────────────────────────────────────
async function signOutAndClear() {
  await client.auth.signOut();
  Object.keys(localStorage).forEach(key => {
    if (key.startsWith('sb-')) localStorage.removeItem(key);
  });
}

let currentToken         = null;
let aiSummaryData        = null;
let currentInstitutionId = null;
let isSuperAdmin         = false;
let isCentralAdmin       = false;
let allRecords           = [];
let allSecurityData      = [];
let pendingDeleteId      = null;
let pendingDeleteName    = null;
let pendingRemoveCoordId = null;
let pendingRemoveCoordName = null;
let pendingRevokeKeyId   = null;
let pendingRevokeKeyName = null;
let newKeyRawValue       = null;
let courseUnitsCache     = [];
let coordinatorsData     = [];
let auditLoaded          = false;

document.getElementById('ai-scope')?.addEventListener('change', function() {
  const wrap = document.getElementById('ai-scope-id-wrap');
  if (wrap) wrap.style.display = this.value === 'course_unit' ? '' : 'none';
});

// ── Toast ──────────────────────────────────────────────────────────────────
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `show toast-${type}`;
  setTimeout(() => { t.className = ''; }, 3000);
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, '&#96;');
}

function escapeJsString(value) {
  return String(value ?? '')
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/\r/g, '\\r')
    .replace(/\n/g, '\\n');
}


// ── SESSIONS STATE ────────────────────────────────────────────────────────
let sessionsData = [];
let currentSessionId = null;

// ── LOAD SESSIONS ──────────────────────────────────────────────────────────

async function loadSessions() {
  if (!currentToken) return;

  document.getElementById('sessions-table-wrap').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading sessions...</div>';

  try {
    const instQuery = currentInstitutionId ? `?institution_id=${currentInstitutionId}` : '';
    const resp = await fetch(`${DAZZLING_URL}/admin/sessions${instQuery}`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    const data = await resp.json();
    sessionsData = data.sessions || [];

    if (!sessionsData.length) {
      document.getElementById('sessions-table-wrap').innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📅</div>
          <p>No sessions found.<br>Sessions are created when attendance is taken.</p>
        </div>`;
      return;
    }

    const rows = sessionsData.map(s => {
      const date = s.started_at
        ? new Date(s.started_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
        : s.created_at
        ? new Date(s.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
        : '—';
      const time = s.started_at
        ? new Date(s.started_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) +
          (s.ended_at ? ' – ' + new Date(s.ended_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '')
        : '—';
      const statusBadge = s.status === 'completed' || s.status === 'confirmed'
        ? '<span class="badge badge-success">Completed</span>'
        : '<span class="badge badge-coord">Active</span>';
      const instCell = isSuperAdmin
        ? `<td style="color:var(--muted);font-size:0.8rem;">${escapeHtml(s.institution_id || '—')}</td>`
        : '';
      const safeId = (s.id || '').replace(/'/g, "\\'");

      return `
        <tr>
          <td>
            <strong>${escapeHtml(s.course_unit_name || s.name || 'N/A')}</strong>
            ${s.course_unit_code ? `<div style="color:var(--muted);font-size:0.78rem;">${escapeHtml(s.course_unit_code)}</div>` : ''}
          </td>
          <td style="color:var(--muted);font-size:0.85rem;">${date}</td>
          <td style="color:var(--muted);font-size:0.85rem;">${time}</td>
          <td>${statusBadge}</td>
          ${instCell}
          <td style="color:var(--muted);font-size:0.78rem;">${escapeHtml(s.lecturer_name || 'Unknown')}</td>
          <td>
            <button class="btn-view" onclick="viewSessionDetails('${safeId}')">View Details</button>
          </td>
        </tr>
      `;
    }).join('');

    const instHeader = isSuperAdmin ? '<th>Institution</th>' : '';
    document.getElementById('sessions-table-wrap').innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Course Unit</th>
            <th>Date</th>
            <th>Time</th>
            <th>Status</th>
            ${instHeader}
            <th>Created By</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="table-footer">${sessionsData.length} session${sessionsData.length !== 1 ? 's' : ''}</div>
    `;
  } catch (e) {
    document.getElementById('sessions-table-wrap').innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${escapeHtml(e.message)}</div>`;
  }
}

// ── VIEW SESSION DETAILS ───────────────────────────────────────────────────
async function viewSessionDetails(sessionId) {
  currentSessionId = sessionId;
  document.getElementById('session-details-modal').classList.add('visible');
  document.getElementById('session-modal-content').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading session details...</div>';

  try {
    const resp = await fetch(`${DAZZLING_URL}/admin/sessions/${sessionId}`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    const data = await resp.json();
    const session = data.session;
    const stats = data.statistics;
    const records = data.records || [];

    const date = session.started_at
      ? new Date(session.started_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
      : session.created_at
      ? new Date(session.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
      : '—';

    const time = session.started_at
      ? new Date(session.started_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) +
        (session.ended_at ? ' – ' + new Date(session.ended_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '')
      : '—';

    document.getElementById('session-modal-title').textContent = 
      `Session: ${session.course_unit_name || 'N/A'}`;

    const recordRows = records.length > 0 
      ? records.map(r => {
          const ts = r.timestamp 
            ? new Date(r.timestamp).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
            : '—';
          const statusBadge = r.verified === 'success'
            ? '<span class="badge badge-success">Success</span>'
            : r.verified === 'spoof'
            ? '<span class="badge badge-spoof">Spoof</span>'
            : '<span class="badge badge-failed">Failed</span>';
          const conf = r.confidence ? (r.confidence * 100).toFixed(1) + '%' : '—';

          return `
            <tr>
              <td>${escapeHtml(r.student_id || '—')}</td>
              <td>${statusBadge}</td>
              <td style="color:var(--muted)">${conf}</td>
              <td style="color:var(--muted);font-size:0.85rem;">${ts}</td>
            </tr>
          `;
        }).join('')
      : '<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:24px;">No attendance records yet</td></tr>';

    document.getElementById('session-modal-content').innerHTML = `
      <div class="session-details-grid">
        <div class="session-detail-card">
          <div class="detail-label">Date</div>
          <div class="detail-value">${date}</div>
        </div>
        <div class="session-detail-card">
          <div class="detail-label">Time</div>
          <div class="detail-value">${time}</div>
        </div>
        <div class="session-detail-card">
          <div class="detail-label">Course Unit</div>
          <div class="detail-value">${escapeHtml(session.course_unit_name || 'N/A')}</div>
          ${session.course_unit_code ? `<div class="detail-sub">${escapeHtml(session.course_unit_code)}</div>` : ''}
        </div>
        <div class="session-detail-card">
          <div class="detail-label">Lecturer</div>
          <div class="detail-value">${escapeHtml(session.lecturer_name || 'Unknown')}</div>
          ${session.lecturer_email ? `<div class="detail-sub">${escapeHtml(session.lecturer_email)}</div>` : ''}
        </div>
      </div>

      <div class="session-stats-grid">
        <div class="stat-card cyan">
          <div class="stat-label">Total Records</div>
          <div class="stat-value">${stats.total_records}</div>
        </div>
        <div class="stat-card blue">
          <div class="stat-label">Verified</div>
          <div class="stat-value">${stats.verified}</div>
        </div>
        <div class="stat-card orange">
          <div class="stat-label">Failed</div>
          <div class="stat-value">${stats.failed}</div>
        </div>
        <div class="stat-card red">
          <div class="stat-label">Spoofs</div>
          <div class="stat-value">${stats.spoof}</div>
        </div>
        <div class="stat-card purple">
          <div class="stat-label">Success Rate</div>
          <div class="stat-value">${stats.success_rate}%</div>
        </div>
      </div>

      <div class="session-records-section">
        <h4 style="margin-bottom:12px;font-size:0.95rem;">Attendance Records</h4>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Student ID</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>${recordRows}</tbody>
          </table>
        </div>
      </div>
    `;
  } catch (e) {
    document.getElementById('session-modal-content').innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${escapeHtml(e.message)}</div>`;
  }
}

function closeSessionDetailsModal() {
  currentSessionId = null;
  document.getElementById('session-details-modal').classList.remove('visible');
}



// ── Tab switching ──────────────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

  const btn = document.getElementById(`tab-btn-${tab}`);
  if (btn) btn.classList.add('active');
  const panel = document.getElementById(`tab-${tab}`);
  if (panel) panel.classList.add('active');

  if (tab === 'students')   loadStudents();
  if (tab === 'superadmin') loadInstitutions();
  if (tab === 'team')       loadCoordinators();
  if (tab === 'lecturers')  { console.log('[dashboard] switchTab: lecturers'); loadLecturers(); }
  if (tab === 'sessions')   loadSessions();
  if (tab === 'departments') loadDepartments();
  if (tab === 'deptadmins')  loadDeptAdmins();
  if (tab === 'apikeys')    loadApiKeys();
  if (tab === 'billing')    loadBilling();
  if (tab === 'analytics') loadAnalytics();
  if (tab === 'security')   loadSecurityData();
  if (tab === 'units')      loadCourseUnits();

  // FIX 3: Populate institution picker for super admins when AI Summary tab opens
  if (tab === 'aisummary') {
    populateAIScopeUnits();

    if (isSuperAdmin) {
      const sel = document.getElementById('ai-filter-institution');
      if (sel && sel.options.length <= 1) {
        fetch(`${DAZZLING_URL}/admin/institutions`, {
          headers: { 'Authorization': `Bearer ${currentToken}` }
        })
        .then(r => r.json())
        .then(data => {
          const insts = data.institutions || [];
          sel.innerHTML = '<option value="">— Select institution —</option>' +
            insts.map(i =>
              `<option value="${escapeAttr(i.id)}">${escapeHtml(i.name || i.id)}</option>`
            ).join('');
        })
        .catch(() => {});
      }
    }
  }

  if (tab === 'audit') {
    if (!auditLoaded) {
      auditLoaded = true;
      auditLoadActionFilter();
      if (isSuperAdmin) {
        document.getElementById('audit-institution-filter-wrap').style.display = '';
        fetch(`${DAZZLING_URL}/admin/institutions`, {
          headers: { 'Authorization': `Bearer ${currentToken}` }
        }).then(r => r.json()).then(data => {
          const insts = data.institutions || [];
          const sel = document.getElementById('audit-filter-institution');
          sel.innerHTML = '<option value="">All Institutions</option>' +
            insts.map(i => `<option value="${escapeAttr(i.id)}">${escapeHtml(i.id)} — ${escapeHtml(i.name)}</option>`).join('');
        }).catch(() => {});
      }
    }
    auditLoadPage(1);
  }
}

// ── Auto-login from Flutter WebView token injection ────────────────────────
async function autoLoginWithToken(accessToken, refreshToken) {
  if (!accessToken) return;
  try {
    const { data, error } = await client.auth.setSession({
      access_token:  accessToken,
      refresh_token: refreshToken,
    });
    if (data?.session) await initDashboard(data.session, true);
  } catch (e) {
    console.error('Auto-login failed:', e);
  }
}

// ── Page load: check for Supabase recovery hash OR existing session ────────
window.addEventListener('load', async () => {
  const hash = window.location.hash;
  if (hash && hash.includes('type=recovery')) {
    let recoveryScreenShown = false;
    const showRecoveryScreenOnce = () => {
      if (recoveryScreenShown) return;
      recoveryScreenShown = true;
      showSetNewPasswordScreen();
    };

    const { data: authListener } = client.auth.onAuthStateChange((event, session) => {
      if (event === 'PASSWORD_RECOVERY' || (event === 'SIGNED_IN' && session)) {
        showRecoveryScreenOnce();
      }
    });

    const { data: sessionData } = await client.auth.getSession();
    if (sessionData?.session) {
      showRecoveryScreenOnce();
    } else {
      const hashParams = new URLSearchParams(hash.substring(1));
      const accessToken = hashParams.get('access_token');
      const refreshToken = hashParams.get('refresh_token') || '';
      if (accessToken) {
        const { data: setData } = await client.auth.setSession({
          access_token: accessToken,
          refresh_token: refreshToken,
        });
        if (setData?.session) showRecoveryScreenOnce();
      }
    }

    if (recoveryScreenShown) authListener?.subscription?.unsubscribe?.();
    return;
  }

  const { data: { session } } = await client.auth.getSession();
  if (session) await initDashboard(session);
});

// ── Set New Password Screen (recovery flow) ────────────────────────────────
function showSetNewPasswordScreen() {
  document.getElementById('login-screen').style.display       = 'none';
  document.getElementById('dashboard-screen').style.display   = 'none';
  document.getElementById('set-new-pw-screen').style.display  = 'flex';
  setTimeout(() => document.getElementById('set-pw-new').focus(), 100);
}

function updatePwStrength(pw) {
  const fill = document.getElementById('pw-strength-fill');
  let score = 0;
  if (pw.length >= 8)          score++;
  if (pw.length >= 12)         score++;
  if (/[A-Z]/.test(pw))        score++;
  if (/[0-9]/.test(pw))        score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  const colors = ['#EF4444','#F59E0B','#F59E0B','#10B981','#10B981'];
  fill.style.width      = `${(score / 5) * 100}%`;
  fill.style.background = colors[score - 1] || 'rgba(255,255,255,0.06)';
}

async function confirmSetNewPassword() {
  const pw1  = document.getElementById('set-pw-new').value;
  const pw2  = document.getElementById('set-pw-confirm').value;
  const btn  = document.getElementById('set-pw-btn');
  const msg  = document.getElementById('set-pw-msg');
  msg.style.display = 'none';

  if (!pw1 || pw1.length < 8) {
    msg.textContent = 'Password must be at least 8 characters.';
    msg.className = 'set-pw-msg error'; msg.style.display = 'block'; return;
  }
  if (pw1 !== pw2) {
    msg.textContent = 'Passwords do not match.';
    msg.className = 'set-pw-msg error'; msg.style.display = 'block'; return;
  }

  btn.disabled = true; btn.textContent = 'Updating…';

  try {
    const { error } = await client.auth.updateUser({ password: pw1 });
    if (error) throw error;

    msg.textContent = '✓ Password updated! Redirecting to sign in…';
    msg.className = 'set-pw-msg success'; msg.style.display = 'block';
    document.getElementById('set-pw-fields').style.display = 'none';

    setTimeout(() => {
      window.location.hash = '';
      document.getElementById('set-new-pw-screen').style.display = 'none';
      document.getElementById('login-screen').style.display      = 'flex';
    }, 2000);
  } catch (err) {
    msg.textContent = err.message || 'Failed to update password.';
    msg.className = 'set-pw-msg error'; msg.style.display = 'block';
    btn.disabled = false; btn.textContent = 'Update Password';
  }
}

// ── Forgot Password Modal ──────────────────────────────────────────────────
function openForgotModal() {
  document.getElementById('forgot-email').value    = '';
  document.getElementById('forgot-email').disabled = false;
  const msg = document.getElementById('forgot-msg');
  msg.style.display = 'none'; msg.className = 'forgot-pw-msg';
  const btn = document.getElementById('forgot-submit-btn');
  btn.disabled = false; btn.textContent = 'Send Link'; btn.style.display = '';
  document.getElementById('forgot-fields').style.display = '';
  document.getElementById('forgot-modal').classList.add('visible');
  setTimeout(() => document.getElementById('forgot-email').focus(), 100);
}

function closeForgotModal() {
  document.getElementById('forgot-modal').classList.remove('visible');
}

async function sendResetLink() {
  const email = document.getElementById('forgot-email').value.trim();
  const msg   = document.getElementById('forgot-msg');
  const btn   = document.getElementById('forgot-submit-btn');
  msg.style.display = 'none';

  if (!email) {
    msg.textContent = 'Please enter your email address.';
    msg.className = 'forgot-pw-msg error'; msg.style.display = 'block'; return;
  }

  btn.disabled = true; btn.textContent = 'Sending…';

  try {
    const resp = await fetch(`${DAZZLING_URL}/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data?.detail || data?.message || 'Failed to send reset link.');

    msg.textContent = data?.message || '✓ Reset link sent — check your inbox.';
    msg.className = 'forgot-pw-msg success'; msg.style.display = 'block';
    btn.style.display = 'none';
    document.getElementById('forgot-email').disabled = true;
  } catch (err) {
    msg.textContent = err.message || 'Failed to send reset link.';
    msg.className = 'forgot-pw-msg error'; msg.style.display = 'block';
    btn.disabled = false; btn.textContent = 'Send Link';
  }
}

// ── Manual login ──────────────────────────────────────────────────────────
async function login() {
  const emailEl    = document.getElementById('login-email');
  const passwordEl = document.getElementById('login-password');
  const email      = emailEl.value.trim();
  const password   = passwordEl.value;
  const btn        = document.getElementById('login-btn');
  const errEl      = document.getElementById('login-error');

  if (!email || !password) { showLoginError("Please enter email and password."); return; }

  btn.disabled    = true;
  btn.textContent = 'Signing in...';
  errEl.style.display = 'none';

  const { data, error } = await client.auth.signInWithPassword({ email, password });

  if (error) {
    showLoginError(error.message);
    btn.disabled    = false;
    btn.textContent = 'Sign In';
    return;
  }

  const { data: profile } = await client
    .from('profiles')
    .select('is_admin, is_super_admin, institution_id')
    .eq('id', data.user.id)
    .single();

  const isAdmin           = profile && (profile.is_admin === true || profile.is_admin === 'true');
  const isSuperAdminCheck = profile && (profile.is_super_admin === true || profile.is_super_admin === 'true');
  const isCentralAdminCheck = profile?.role === 'central_admin';

  if (!profile || !(isAdmin || isSuperAdminCheck || isCentralAdminCheck)) {
    showLoginError("Access denied. Admin account required.");
    await client.auth.signOut();
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith('sb-')) localStorage.removeItem(key);
    });
    btn.disabled    = false;
    btn.textContent = 'Sign In';
    return;
  }

  if (!isSuperAdminCheck && profile.institution_id) {
    const { data: inst } = await client
      .from('institutions')
      .select('status')
      .eq('id', profile.institution_id)
      .single();

    const status = inst?.status?.toLowerCase().trim();

    if (status === 'suspended') {
      showLoginError('Your institution has been suspended. Contact support.');
      await client.auth.signOut();
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('sb-')) localStorage.removeItem(key);
      });
      btn.disabled    = false;
      btn.textContent = 'Sign In';
      return;
    }

    if (status === 'pending') {
      showLoginError('Your institution is pending approval.');
      await client.auth.signOut();
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('sb-')) localStorage.removeItem(key);
      });
      btn.disabled    = false;
      btn.textContent = 'Sign In';
      return;
    }
  }

  emailEl.value    = '';
  passwordEl.value = '';
  btn.disabled     = false;
  btn.textContent  = 'Sign In';

  await initDashboard(data.session, true);
}

function showLoginError(msg) {
  const el = document.getElementById('login-error');
  el.textContent   = msg;
  el.style.display = 'block';
}

// ── Init dashboard ─────────────────────────────────────────────────────────
async function initDashboard(session, isFreshLogin = false) {
  currentToken = session.access_token;

  try {
    const { data: profile, error } = await client
      .from('profiles')
      .select('institution_id, is_super_admin, role')
      .eq('id', session.user.id)
      .single();

    if (error) throw error;

    currentInstitutionId = profile?.institution_id || null;
    isSuperAdmin         = profile?.is_super_admin === true;
    isCentralAdmin       = profile?.role === 'central_admin';

    if (!isSuperAdmin && currentInstitutionId) {
      const { data: inst } = await client
        .from('institutions')
        .select('status')
        .eq('id', currentInstitutionId)
        .single();

      const status = inst?.status?.toLowerCase().trim();

      if (status === 'suspended') {
        await signOutAndClear();
        document.getElementById('login-screen').style.display = 'flex';
        document.getElementById('dashboard-screen').style.display = 'none';
        showLoginError('Your institution has been suspended. Contact support.');
        return;
      }

      if (status === 'pending') {
        await signOutAndClear();
        document.getElementById('login-screen').style.display = 'flex';
        document.getElementById('dashboard-screen').style.display = 'none';
        showLoginError('Your institution is pending approval.');
        return;
      }
    }

    if (isFreshLogin) {
      try {
        const logResp = await fetch(`${DAZZLING_URL}/auth/log-login`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${currentToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ source: 'dashboard' }),
        });
        if (!logResp.ok) {
          const errBody = await logResp.json().catch(() => ({}));
          console.warn('log-login failed:', logResp.status, errBody.detail || errBody.message || logResp.statusText);
        }
      } catch (e) {
        console.warn('log-login failed:', e);
      }
    }

    const tabs = document.getElementById('tabs');
    tabs.innerHTML = '';

    const createSecureTab = (id, text, targetTab, classNames) => {
      const btn = document.createElement('button');
      btn.className = `tab-btn ${classNames}`;
      btn.id = id;
      btn.textContent = text;
      btn.addEventListener('click', () => switchTab(targetTab));
      return btn;
    };

    tabs.appendChild(createSecureTab('tab-btn-attendance', '📅 Attendance', 'attendance', 'attendance-tab'));
    tabs.appendChild(createSecureTab('tab-btn-aisummary', '🤖 AI Summary', 'aisummary', ''));

    if (isCentralAdmin) {
      // ── Central Admin: departments, dept admins, billing, audit only ─────────
      tabs.appendChild(createSecureTab('tab-btn-departments', '🏛️ Departments', 'departments', ''));
      tabs.appendChild(createSecureTab('tab-btn-deptadmins', '👤 Dept Admins', 'deptadmins', ''));
      tabs.appendChild(createSecureTab('tab-btn-billing', '💳 Billing', 'billing', 'billing-tab'));
      tabs.appendChild(createSecureTab('tab-btn-audit', '📋 Audit Logs', 'audit', 'audit-tab'));

    } else if (isSuperAdmin) {
      // ── Super Admin: everything ───────────────────────────────────────────────
      tabs.appendChild(createSecureTab('tab-btn-students', '👥 Students', 'students', ''));
      tabs.appendChild(createSecureTab('tab-btn-lecturers', '👨‍🏫 Lecturers', 'lecturers', ''));
      tabs.appendChild(createSecureTab('tab-btn-units', '📚 Course Units', 'units', 'units-tab'));
      tabs.appendChild(createSecureTab('tab-btn-sessions', '📅 Sessions', 'sessions', ''));
      tabs.appendChild(createSecureTab('tab-btn-team', 'Team', 'team', ''));

      const teamInstFilter = document.getElementById('filter-team-inst');
      teamInstFilter.style.display = '';
      fetch(`${DAZZLING_URL}/admin/institutions`, {
        headers: { 'Authorization': `Bearer ${currentToken}` }
      })
      .then(r => r.json())
      .then(data => {
        const insts = data.institutions || [];
        teamInstFilter.innerHTML = '<option value="">All Institutions</option>' +
          insts.map(i => `<option value="${i.id}">${i.id} — ${i.name}</option>`).join('');
      }).catch(() => {});

      const aiInstWrap = document.getElementById('ai-institution-wrap');
      if (aiInstWrap) aiInstWrap.style.display = '';

      tabs.appendChild(createSecureTab('tab-btn-apikeys', '⚙ API Keys', 'apikeys', 'dev-tab'));

      const adminTabBtn = document.createElement('button');
      adminTabBtn.className = 'tab-btn superadmin-tab';
      adminTabBtn.id = 'tab-btn-superadmin';
      adminTabBtn.innerHTML = '🏢 Institutions <span class="pending-count" id="pending-count" style="display:none"></span>';
      adminTabBtn.addEventListener('click', () => switchTab('superadmin'));
      tabs.appendChild(adminTabBtn);

      tabs.appendChild(createSecureTab('tab-btn-security', '🛡 Security', 'security', 'security-tab'));
      tabs.appendChild(createSecureTab('tab-btn-audit', '📋 Audit Logs', 'audit', 'audit-tab'));
      tabs.appendChild(createSecureTab('tab-btn-analytics', '📊 Analytics', 'analytics', 'superadmin-tab'));

    } else {
      // ── Dept Admin (role='admin'): students, team, lecturers, units, billing ──
      tabs.appendChild(createSecureTab('tab-btn-students', '👥 Students', 'students', ''));
      tabs.appendChild(createSecureTab('tab-btn-lecturers', '👨‍🏫 Lecturers', 'lecturers', ''));

      if (currentInstitutionId) {
        tabs.appendChild(createSecureTab('tab-btn-units', '📚 Course Units', 'units', 'units-tab'));
      }

      tabs.appendChild(createSecureTab('tab-btn-sessions', '📅 Sessions', 'sessions', ''));
      tabs.appendChild(createSecureTab('tab-btn-team', 'Team', 'team', ''));
      tabs.appendChild(createSecureTab('tab-btn-billing', '💳 Billing', 'billing', 'billing-tab'));
      tabs.appendChild(createSecureTab('tab-btn-apikeys', '⚙ API Keys', 'apikeys', 'dev-tab'));
      tabs.appendChild(createSecureTab('tab-btn-audit', '📋 Audit Logs', 'audit', 'audit-tab'));
    }

    if (!isSuperAdmin && currentInstitutionId) {
      const { data: units } = await client
        .from('course_units')
        .select('id, name, code')
        .eq('institution_id', currentInstitutionId)
        .order('created_at', { ascending: true });
      courseUnitsCache = units || [];
      populateAIScopeUnits();
    }

    switchTab('attendance');
    await loadData();
    if (isSuperAdmin) await fetchPendingCount();

    document.getElementById('nav-user').textContent = session.user.email;
    document.getElementById('nav-superadmin').style.display = isSuperAdmin ? '' : 'none';

    const navInst = document.getElementById('nav-inst');
    if (currentInstitutionId) {
      navInst.textContent = currentInstitutionId;
      navInst.style.display = '';
    } else {
      navInst.style.display = 'none';
    }

    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('dashboard-screen').style.display = 'block';

  } catch (err) {
    console.error('Critical initialization failure:', err);
    alert('Failed to securely initialize your dashboard session. Please login again.');
  }
}

// ── AI SUMMARY TAB ─────────────────────────────────────────────────────────
async function populateAIScopeUnits() {
  const sel = document.getElementById('ai-scope-id');
  const scopeSel = document.getElementById('ai-scope');
  if (scopeSel && !currentInstitutionId && isSuperAdmin) {
    const institutionOption = scopeSel.querySelector('option[value="institution"]');
    if (institutionOption) institutionOption.textContent = 'All Institutions';
  }
  if (!sel) return;
  sel.innerHTML = '<option value="">— Select unit —</option>' +
    courseUnitsCache.map(u =>
      `<option value="${escapeAttr(u.id)}">${escapeHtml(u.name)}${u.code ? ' (' + escapeHtml(u.code) + ')' : ''}</option>`
    ).join('');
}

// FIX 4: generateAISummary — always send institution_id, reading from picker for super admins
async function generateAISummary() {
  const btn      = document.getElementById('ai-generate-btn');
  const preview  = document.getElementById('ai-summary-preview');
  const scope    = document.getElementById('ai-scope').value;
  const scopeId  = document.getElementById('ai-scope-id').value;
  const dateFrom = document.getElementById('ai-date-from').value;
  const dateTo   = document.getElementById('ai-date-to').value;

  // Super admin reads institution from the picker; regular admin uses their profile institution
  const instPickerEl = document.getElementById('ai-filter-institution');
  const effectiveInstId = isSuperAdmin
    ? (instPickerEl ? instPickerEl.value : '')
    : currentInstitutionId;

  if (isSuperAdmin && !effectiveInstId) {
    showToast('Please select an institution first', 'error');
    return;
  }

  if (scope === 'course_unit' && !scopeId) {
    showToast('Please select a course unit', 'error');
    return;
  }

  if (btn) { btn.disabled = true; btn.textContent = '⏳ Generating...'; }
  if (preview) preview.classList.remove('visible');

  try {
    const params = new URLSearchParams({ scope });
    if (scopeId)         params.set('scope_id', scopeId);
    if (dateFrom)        params.set('date_from', dateFrom);
    if (dateTo)          params.set('date_to', dateTo);
    if (effectiveInstId) params.set('institution_id', effectiveInstId);

    const resp = await fetch(`${API_URL}/admin/ai-attendance-summary?${params}`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Failed to generate summary');

    aiSummaryData = data;
    renderAISummary(data);
    if (preview) preview.classList.add('visible');
    preview?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    showToast(
      data.truncated
        ? '✓ Summary generated (latest 1000 records only)'
        : '✓ Summary generated',
      'success'
    );
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '✦ Generate'; }
  }
}

function renderAISummary(data) {
  const stats = data.stats || {};
  const metaParts = [data.institution];
  if (data.scope === 'course_unit' && (data.course_unit_name || data.scope_id)) {
    metaParts.push(`Course Unit: ${data.course_unit_name || data.scope_id}`);
  }
  if (data.date_from || data.date_to) metaParts.push(`${data.date_from || '...'} → ${data.date_to || 'today'}`);
  metaParts.push(new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }));
  document.getElementById('ai-preview-meta').textContent = metaParts.join(' · ');

  const riskColor = stats.at_risk_count > 0 ? 'var(--red)' : 'var(--cyan)';
  document.getElementById('ai-stats-strip').innerHTML = `
    <div class="ai-stat">
      <div class="ai-stat-label">Students</div>
      <div class="ai-stat-value">${stats.total_students ?? '—'}</div>
    </div>
    <div class="ai-stat">
      <div class="ai-stat-label">Total Records</div>
      <div class="ai-stat-value">${stats.total_records ?? '—'}</div>
    </div>
    <div class="ai-stat">
      <div class="ai-stat-label">Avg Attendance</div>
      <div class="ai-stat-value" style="color:var(--cyan)">${stats.overall_attendance_pct ?? '—'}%</div>
    </div>
    <div class="ai-stat">
      <div class="ai-stat-label">At Risk</div>
      <div class="ai-stat-value" style="color:${riskColor}">${stats.at_risk_count ?? '—'}</div>
    </div>
  `;

  document.getElementById('ai-summary-text').textContent = data.summary || '';
  const atRisk = data.at_risk || [];
  if (atRisk.length) {
    document.getElementById('ai-at-risk-table').innerHTML = `
      <div class="ai-at-risk-title">⚠ At-Risk Students (below 75%)</div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Student</th><th>Attendance</th><th>Rate</th></tr></thead>
          <tbody>${atRisk.map(s => `
            <tr>
              <td>${escapeHtml(s.name)}</td>
              <td style="color:var(--red);font-weight:600;">${s.attendance_pct}%</td>
              <td><div style="height:6px;border-radius:3px;background:rgba(255,255,255,0.06);overflow:hidden;"><div style="height:6px;border-radius:3px;background:var(--red);width:${s.attendance_pct}%;"></div></div></td>
            </tr>`).join('')}</tbody>
        </table>
      </div>`;
  } else {
    document.getElementById('ai-at-risk-table').innerHTML =
      `<div class="ai-at-risk-title" style="color:var(--cyan)">✓ No at-risk students</div>`;
  }
}

function downloadSummaryPDF() {
  if (!aiSummaryData) return;
  const data  = aiSummaryData;
  const stats = data.stats || {};
  const now   = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  const atRiskRows = (data.at_risk || []).map(s =>
    `<tr><td>${escapeHtml(s.name)}</td><td style="color:#ef4444;font-weight:600;">${s.attendance_pct}%</td></tr>`
  ).join('');

  const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"/>
  <title>AI Attendance Report — ${data.institution}</title>
  <style>
    body { font-family: Arial, sans-serif; color: #111; max-width: 750px; margin: 40px auto; padding: 0 24px; }
    h1 { font-size: 1.4rem; margin-bottom: 4px; }
    .meta { color: #666; font-size: 0.82rem; margin-bottom: 24px; }
    .stats { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
    .stat { border: 1px solid #ddd; border-radius: 8px; padding: 12px 16px; flex: 1; min-width: 100px; }
    .stat-label { font-size: 0.68rem; color: #999; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px; }
    .stat-value { font-size: 1.5rem; font-weight: 800; }
    h2 { font-size: 1rem; border-bottom: 2px solid #eee; padding-bottom: 6px; margin: 24px 0 12px; }
    .summary { font-size: 0.88rem; line-height: 1.8; white-space: pre-wrap; }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; }
    th { text-align: left; font-size: 0.72rem; color: #999; text-transform: uppercase; padding: 8px; border-bottom: 1px solid #eee; }
    td { padding: 8px; border-bottom: 1px solid #f0f0f0; font-size: 0.85rem; }
    .footer { margin-top: 40px; font-size: 0.72rem; color: #aaa; text-align: center; }
  </style></head><body>
  <h1>AI Attendance Report — ${escapeHtml(data.institution)}</h1>
  <div class="meta">Generated ${now} · Powered by FaceAttend AI</div>
  <div class="stats">
    <div class="stat"><div class="stat-label">Students</div><div class="stat-value">${stats.total_students ?? '—'}</div></div>
    <div class="stat"><div class="stat-label">Records</div><div class="stat-value">${stats.total_records ?? '—'}</div></div>
    <div class="stat"><div class="stat-label">Avg Attendance</div><div class="stat-value">${stats.overall_attendance_pct ?? '—'}%</div></div>
    <div class="stat"><div class="stat-label">At Risk</div><div class="stat-value" style="color:#ef4444">${stats.at_risk_count ?? '—'}</div></div>
  </div>
  <h2>AI Analysis</h2>
  <div class="summary">${escapeHtml(data.summary || '')}</div>
  ${atRiskRows ? `<h2>At-Risk Students</h2><table><thead><tr><th>Student</th><th>Attendance</th></tr></thead><tbody>${atRiskRows}</tbody></table>` : ''}
  <div class="footer">FaceAttend · faceattend.app · Confidential</div>
  </body></html>`;

  const blob = new Blob([html], { type: 'text/html' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url;
  a.download = `attendance-report-${data.institution}-${new Date().toISOString().slice(0,10)}.html`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('Report downloaded — open in browser and print to PDF', 'success');
}

// ── Pending count badge ────────────────────────────────────────────────────
async function fetchPendingCount() {
  try {
    const resp = await fetch(`${DAZZLING_URL}/admin/institutions?status=pending`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    if (!resp.ok) return;
    const data = await resp.json();
    const count = data.count || 0;
    const badge = document.getElementById('pending-count');
    if (badge && count > 0) {
      badge.textContent   = count;
      badge.style.display = 'inline-block';
    }
  } catch(e) { console.error(e); }
}

async function logout() {
  if (currentToken) {
    try {
      await fetch(`${DAZZLING_URL}/auth/log-logout`, {
        method: 'POST', headers: { 'Authorization': `Bearer ${currentToken}` }
      });
    } catch (e) { console.warn('log-logout failed:', e); }
  }

  await signOutAndClear();

  localStorage.removeItem('lastActivity');
  currentToken         = null;
  currentInstitutionId = null;
  isSuperAdmin         = false;
  isCentralAdmin       = false;
  allRecords           = [];
  allSecurityData      = [];
  courseUnitsCache     = [];
  coordinatorsData     = [];
  auditLoaded          = false;

  ['tab-btn-attendance','tab-btn-students','tab-btn-aisummary','tab-btn-team','tab-btn-units',
   'tab-btn-billing','tab-btn-apikeys','tab-btn-superadmin',
   'tab-btn-security','tab-btn-audit'].forEach(id => {
    document.getElementById(id)?.remove();
  });

  document.querySelectorAll('.tab-btn').forEach((b, i) => b.classList.toggle('active', i === 0));
  document.querySelectorAll('.tab-panel').forEach((p, i) => p.classList.toggle('active', i === 0));

  document.getElementById('nav-superadmin').style.display = 'none';
  document.getElementById('nav-inst').style.display       = 'none';
  document.getElementById('filter-inst').style.display    = '';

  // Reset the institution picker for next login
  const aiInstWrap = document.getElementById('ai-institution-wrap');
  if (aiInstWrap) aiInstWrap.style.display = 'none';
  const aiInstSel = document.getElementById('ai-filter-institution');
  if (aiInstSel) aiInstSel.innerHTML = '<option value="">— Select institution —</option>';

  document.getElementById('login-email').value    = '';
  document.getElementById('login-password').value = '';
  document.getElementById('login-error').style.display = 'none';

  document.getElementById('new-key-banner').classList.remove('visible');
  newKeyRawValue = null;

  document.getElementById('login-screen').style.display    = 'flex';
  document.getElementById('dashboard-screen').style.display = 'none';
}

// ── Load attendance data ───────────────────────────────────────────────────
async function loadData() {
  if (!currentToken) return;
  const headers = { 'Authorization': `Bearer ${currentToken}` };

  document.getElementById('table-wrap').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading records...</div>';

  try {
    const instParam = currentInstitutionId ? `&institution_id=${currentInstitutionId}` : '';
    const instQuery = currentInstitutionId ? `?institution_id=${currentInstitutionId}` : '';

    const [recResp, studResp] = await Promise.all([
      fetch(`${API_URL}/admin/attendance-records?limit=1000${instParam}`, { headers }),
      fetch(`${DAZZLING_URL}/students${instQuery}`, { headers }),
    ]);

    const records  = recResp.ok  ? await recResp.json()  : [];
    const studData = studResp.ok ? await studResp.json() : { count: 0 };

    allRecords = Array.isArray(records) ? records : [];
    const totalStudents = studData.count || 0;

    const total    = allRecords.length;
    const verified = allRecords.filter(r => r.verified === 'success').length;
    const failed   = allRecords.filter(r => r.verified === 'failed').length;
    const spoofs   = allRecords.filter(r => r.verified === 'spoof').length;
    const rate     = total > 0 ? Math.round(verified / total * 100) : 0;

    document.getElementById('metrics').innerHTML = `
      <div class="metric-card cyan">
        <div class="metric-label">Verified</div>
        <div class="metric-value">${verified}</div>
        <div class="metric-sub">successful scans</div>
      </div>
      <div class="metric-card blue">
        <div class="metric-label">Total Students</div>
        <div class="metric-value">${totalStudents}</div>
        <div class="metric-sub">enrolled</div>
      </div>
      <div class="metric-card orange">
        <div class="metric-label">Failed + Spoofs</div>
        <div class="metric-value">${failed + spoofs}</div>
        <div class="metric-sub">${spoofs} spoof attempts</div>
      </div>
      <div class="metric-card purple">
        <div class="metric-label">Success Rate</div>
        <div class="metric-value">${rate}%</div>
        <div class="metric-sub">recognition accuracy</div>
      </div>
    `;

    if (!currentInstitutionId) {
      const insts = [...new Set(allRecords.map(r => r.institution_id).filter(Boolean))].sort();
      document.getElementById('filter-inst').innerHTML =
        '<option value="">All Institutions</option>' +
        insts.map(i => `<option value="${i}">${i}</option>`).join('');
    }

    renderTable(allRecords);

  } catch (e) {
    document.getElementById('table-wrap').innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${e.message}</div>`;
  }
}

// ── SECURITY TAB ───────────────────────────────────────────────────────────
async function loadSecurityData() {
  if (!currentToken || !isSuperAdmin) return;

  document.getElementById('security-table-wrap').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading security data...</div>';
  document.getElementById('security-summary-grid').innerHTML = '';

  try {
    const periodDays = document.getElementById('security-filter-period').value;
    const resp = await fetch(`${API_URL}/admin/attendance-records?limit=5000`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    if (!resp.ok) throw new Error('Failed to fetch records');
    let records = await resp.json();
    records = Array.isArray(records) ? records : [];

    if (periodDays !== 'all') {
      const cutoff = Date.now() - parseInt(periodDays) * 24 * 60 * 60 * 1000;
      records = records.filter(r => r.timestamp && new Date(r.timestamp).getTime() >= cutoff);
    }

    allSecurityData = records;

    const byInst = {};
    for (const r of records) {
      const id = r.institution_id || 'Unknown';
      if (!byInst[id]) byInst[id] = { spoof: 0, failed: 0, success: 0, total: 0 };
      byInst[id].total++;
      if (r.verified === 'spoof')   byInst[id].spoof++;
      if (r.verified === 'failed')  byInst[id].failed++;
      if (r.verified === 'success') byInst[id].success++;
    }

    const rows = Object.entries(byInst).sort((a, b) => b[1].spoof - a[1].spoof);

    const totalSpoofs  = rows.reduce((s, [, v]) => s + v.spoof, 0);
    const totalFailed  = rows.reduce((s, [, v]) => s + v.failed, 0);
    const totalSuccess = rows.reduce((s, [, v]) => s + v.success, 0);
    const flagged      = rows.filter(([, v]) => v.total > 0 && (v.spoof / v.total) >= 0.1).length;

    document.getElementById('security-summary-grid').innerHTML = `
      <div class="security-card red">
        <div class="metric-label">Total Spoofs</div>
        <div class="metric-value" style="color:var(--red)">${totalSpoofs}</div>
        <div class="metric-sub">spoof attempts</div>
      </div>
      <div class="security-card orange">
        <div class="metric-label">Total Failed</div>
        <div class="metric-value" style="color:var(--orange)">${totalFailed}</div>
        <div class="metric-sub">failed verifications</div>
      </div>
      <div class="security-card cyan">
        <div class="metric-label">Successful</div>
        <div class="metric-value" style="color:var(--cyan)">${totalSuccess}</div>
        <div class="metric-sub">verified scans</div>
      </div>
      <div class="security-card yellow">
        <div class="metric-label">Flagged Institutions</div>
        <div class="metric-value" style="color:var(--yellow)">${flagged}</div>
        <div class="metric-sub">spoof rate ≥ 10%</div>
      </div>
    `;

    if (!rows.length) {
      document.getElementById('security-table-wrap').innerHTML =
        '<div class="loading">No security records found for this period.</div>';
      return;
    }

    const maxSpoof = Math.max(...rows.map(([, v]) => v.spoof), 1);

    const tableRows = rows.map(([instId, v]) => {
      const spoofRate = v.total > 0 ? ((v.spoof / v.total) * 100).toFixed(1) : '0.0';
      const isFlagged = v.total > 0 && (v.spoof / v.total) >= 0.1;
      const barWidth  = Math.round((v.spoof / maxSpoof) * 100);
      const barColor  = isFlagged ? 'var(--red)' : v.spoof > 0 ? 'var(--orange)' : 'var(--muted)';
      const flagMark  = isFlagged ? '<span class="flag-badge"></span>' : '';
      const rowClass  = isFlagged ? 'flag-row' : '';

      return `
        <tr class="${rowClass}" id="row-${instId}">
          <td><strong>${flagMark}${instId}</strong></td>
          <td style="color:var(--red);font-weight:600;">${v.spoof}</td>
          <td style="color:var(--orange)">${v.failed}</td>
          <td style="color:var(--cyan)">${v.success}</td>
          <td>
            <div class="spoof-rate-row">
              <div class="spoof-rate-bg">
                <div class="spoof-rate-fill" style="width:${barWidth}%;background:${barColor};"></div>
              </div>
              <span style="font-size:0.78rem;color:${isFlagged ? 'var(--red)' : 'var(--muted)'};min-width:38px;">${spoofRate}%</span>
            </div>
          </td>
          <td>
            <button class="drill-btn" id="drill-btn-${instId}" onclick="toggleDrill('${instId}')">View Logs</button>
          </td>
        </tr>
        <tr id="drill-${instId}" style="display:none;">
          <td colspan="6" style="padding:0;">
            <div class="drill-panel" id="drill-content-${instId}"></div>
          </td>
        </tr>
      `;
    }).join('');

    document.getElementById('security-table-wrap').innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Institution</th><th>Spoof Attempts</th><th>Failed Verifications</th>
            <th>Successful Scans</th><th>Spoof Rate</th><th>Drill Down</th>
          </tr>
        </thead>
        <tbody>${tableRows}</tbody>
      </table>
      <div class="security-note">
        <span class="flag-badge"></span>
        Institutions with spoof rate ≥ 10% are flagged in red. Click "View Logs" to see individual attempts.
      </div>
    `;

  } catch (e) {
    document.getElementById('security-table-wrap').innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${e.message}</div>`;
  }
}

function toggleDrill(instId) {
  const drillRow     = document.getElementById(`drill-${instId}`);
  const drillContent = document.getElementById(`drill-content-${instId}`);
  const drillBtn     = document.getElementById(`drill-btn-${instId}`);

  const isOpen = drillRow.style.display !== 'none';
  if (isOpen) {
    drillRow.style.display = 'none';
    drillBtn.classList.remove('active');
    drillBtn.textContent = 'View Logs';
    return;
  }

  drillRow.style.display = 'table-row';
  drillBtn.classList.add('active');
  drillBtn.textContent = 'Hide Logs';

  const periodDays = document.getElementById('security-filter-period').value;
  let cutoff = null;
  if (periodDays !== 'all') cutoff = Date.now() - parseInt(periodDays) * 24 * 60 * 60 * 1000;

  const records = allSecurityData.filter(r => {
    const matchInst   = (r.institution_id || 'Unknown') === instId;
    const matchStatus = r.verified === 'spoof' || r.verified === 'failed';
    const matchTime   = !cutoff || (r.timestamp && new Date(r.timestamp).getTime() >= cutoff);
    return matchInst && matchStatus && matchTime;
  }).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 50);

  if (!records.length) {
    drillContent.innerHTML = '<div style="padding:16px;color:var(--muted);font-size:0.82rem;">No records found.</div>';
    return;
  }

  const rows = records.map(r => {
    const ts    = r.timestamp ? new Date(r.timestamp).toLocaleString('en-GB', { timeZone: 'Africa/Nairobi' }) : '—';
    const badge = r.verified === 'spoof'
      ? '<span class="badge badge-spoof">Spoof</span>'
      : '<span class="badge badge-failed">Failed</span>';
    const conf = r.confidence ? (r.confidence * 100).toFixed(1) + '%' : '—';
    return `<tr><td>${badge}</td><td>${r.student_id || '—'}</td><td>${conf}</td><td style="color:var(--muted)">${ts}</td></tr>`;
  }).join('');

  drillContent.innerHTML = `
    <table>
      <thead><tr><th>Type</th><th>Student ID</th><th>Confidence</th><th>Time (EAT)</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="table-footer">Showing ${records.length} record${records.length !== 1 ? 's' : ''}${records.length === 50 ? ' (capped at 50)' : ''}</div>
  `;
}

function exportSecurityCSV() {
  const records = allSecurityData.filter(r => r.verified === 'spoof' || r.verified === 'failed');
  if (!records.length) { showToast('No security records to export', 'error'); return; }
  const header = ['institution_id', 'verified', 'student_id', 'confidence', 'timestamp'];
  const rows   = records.map(r => header.map(k => r[k] ?? '').join(','));
  const csv    = [header.join(','), ...rows].join('\n');
  const blob   = new Blob([csv], { type: 'text/csv' });
  const url    = URL.createObjectURL(blob);
  const a      = document.createElement('a');
  a.href = url; a.download = `security_${new Date().toISOString().slice(0,10)}.csv`; a.click();
  URL.revokeObjectURL(url);
}

// ── AUDIT LOGS TAB ─────────────────────────────────────────────────────────
const AUDIT_ACTION_LABELS = {
  'auth.login':                { label: 'Login',                 color: '#4a9eff' },
  'auth.logout':               { label: 'Logout',                color: '#5a5a7a' },
  'auth.password_reset':       { label: 'Password Reset',        color: '#f5c400' },
  'auth.password_change':      { label: 'Password Changed',      color: '#f5c400' },
  'coordinator.invite':        { label: 'Coordinator Invited',   color: '#a78bfa' },
  'coordinator.remove':        { label: 'Coordinator Removed',   color: '#ff5050' },
  'student.create':            { label: 'Student Registered',    color: '#00f5c4' },
  'student.delete':            { label: 'Student Deleted',       color: '#ff5050' },
  'api_key.create':            { label: 'API Key Created',       color: '#00f5c4' },
  'api_key.revoke':            { label: 'API Key Revoked',       color: '#ff5050' },
  'institution.approve':       { label: 'Institution Approved',  color: '#00f5c4' },
  'institution.suspend':       { label: 'Institution Suspended', color: '#ff5050' },
  'attendance.verify':         { label: 'Attendance Verified',   color: '#4a9eff' },
  'attendance.spoof_detected': { label: '⚠ Spoof Detected',      color: '#ff5050' },
};

let auditCurrentPage = 1;

function auditBadge(action) {
  const def = AUDIT_ACTION_LABELS[action] || { label: action, color: '#5a5a7a' };
  return `<span class="audit-action-badge" style="background:${def.color}1a;color:${def.color};border:1px solid ${def.color}33;">${def.label}</span>`;
}

function auditFormatTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  d.setHours(d.getHours() + 3);
  const pad = n => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth()+1)}-${pad(d.getUTCDate())} <span style="color:var(--muted)">${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}</span>`;
}

function auditFormatMeta(meta) {
  if (!meta || !Object.keys(meta).length) return '—';
  const skip = new Set(['ip_address']);
  const parts = Object.entries(meta)
    .filter(([k, v]) => !skip.has(k) && v)
    .map(([k, v]) => `<span style="color:var(--muted)">${escapeHtml(k.replace(/_/g,' '))}:</span> ${escapeHtml(v)}`)
    .join(' &nbsp;·&nbsp; ');
  return parts || '—';
}

async function auditLoadPage(page = 1) {
  auditCurrentPage = page;
  const wrap = document.getElementById('audit-table-wrap');
  wrap.innerHTML = '<div class="loading"><div class="spinner"></div>Loading audit logs...</div>';

  const action      = document.getElementById('audit-filter-action')?.value || '';
  const start       = document.getElementById('audit-filter-start')?.value || '';
  const end         = document.getElementById('audit-filter-end')?.value || '';
  const institution = document.getElementById('audit-filter-institution')?.value || '';

  const params = new URLSearchParams({ page, limit: 50 });
  if (action)      params.set('action', action);
  if (start)       params.set('start_date', start);
  if (end)         params.set('end_date', end);
  if (institution) params.set('institution_id', institution);

  let data;
  try {
    const res = await fetch(`${DAZZLING_URL}/audit-logs?${params}`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    if (!res.ok) throw new Error(await res.text());
    data = await res.json();
  } catch (e) {
    wrap.innerHTML = `<div class="loading" style="color:var(--red)">Error loading logs: ${escapeHtml(e.message)}</div>`;
    return;
  }

  document.getElementById('audit-stats').innerHTML =
    `<span><strong>${data.total || 0}</strong> total events</span>
     <span>Page <strong>${data.page || 1}</strong> of <strong>${data.pages || 1}</strong></span>`;

  if (!data.data?.length) {
    wrap.innerHTML = '<div class="loading">No audit events found.</div>';
  } else {
    const rows = data.data.map(ev => `
      <tr>
        <td style="white-space:nowrap;font-size:0.78rem;">${auditFormatTime(ev.created_at)}</td>
        <td>${auditBadge(ev.action)}</td>
        <td style="color:var(--muted);font-size:0.8rem;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeAttr(ev.actor_email || '')}">
          ${ev.actor_email ? escapeHtml(ev.actor_email) : '<span style="color:var(--muted)">—</span>'}
        </td>
        <td style="font-family:'DM Mono',monospace;font-size:0.75rem;color:var(--muted);">${ev.ip_address || '—'}</td>
        <td style="font-size:0.78rem;color:var(--muted);max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeAttr(JSON.stringify(ev.metadata||{}))}">
          ${auditFormatMeta(ev.metadata)}
        </td>
      </tr>
    `).join('');

    wrap.innerHTML = `
      <table>
        <thead><tr><th>Time (EAT)</th><th>Action</th><th>Actor</th><th>IP Address</th><th>Details</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="table-footer">${data.data.length} events on this page</div>
    `;
  }

  const totalPages = data.pages || 1;
  document.getElementById('audit-pagination').innerHTML = `
    <button onclick="auditLoadPage(${page - 1})" ${page <= 1 ? 'disabled' : ''}>← Prev</button>
    <span>Page ${page} of ${totalPages}</span>
    <button onclick="auditLoadPage(${page + 1})" ${page >= totalPages ? 'disabled' : ''}>Next →</button>
  `;
}

async function auditLoadActionFilter() {
  try {
    const res  = await fetch(`${DAZZLING_URL}/audit-logs/actions`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    if (!res.ok) return;
    const data = await res.json();
    const sel  = document.getElementById('audit-filter-action');
    (data.actions || []).forEach(a => {
      const opt = document.createElement('option');
      opt.value = a; opt.textContent = AUDIT_ACTION_LABELS[a]?.label || a;
      sel.appendChild(opt);
    });
  } catch (e) { /* silent */ }
}

function auditExportCSV() {
  const action      = document.getElementById('audit-filter-action')?.value || '';
  const start       = document.getElementById('audit-filter-start')?.value || '';
  const end         = document.getElementById('audit-filter-end')?.value || '';
  const institution = document.getElementById('audit-filter-institution')?.value || '';
  const params = new URLSearchParams({ page: 1, limit: 200 });
  if (action)      params.set('action', action);
  if (start)       params.set('start_date', start);
  if (end)         params.set('end_date', end);
  if (institution) params.set('institution_id', institution);

  fetch(`${DAZZLING_URL}/audit-logs?${params}`, {
    headers: { 'Authorization': `Bearer ${currentToken}` }
  })
    .then(r => r.json())
    .then(data => {
      const rows = [['Time (UTC)', 'Action', 'Actor', 'IP Address', 'Resource', 'Details']];
      (data.data || []).forEach(ev => {
        rows.push([ev.created_at||'', ev.action||'', ev.actor_email||'', ev.ip_address||'',
          ev.resource_type ? `${ev.resource_type} ${ev.resource_id||''}`.trim() : '',
          JSON.stringify(ev.metadata || {})]);
      });
      const csv  = rows.map(r => r.map(c => `"${String(c).replace(/"/g,'""')}"`).join(',')).join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url; a.download = `faceattend-audit-${new Date().toISOString().slice(0,10)}.csv`; a.click();
      URL.revokeObjectURL(url);
    })
    .catch(e => showToast('Export failed: ' + e.message, 'error'));
}

// ── Load students ──────────────────────────────────────────────────────────
async function loadStudents() {
  if (!currentToken) return;
  const headers   = { 'Authorization': `Bearer ${currentToken}` };
  const instQuery = currentInstitutionId ? `?institution_id=${currentInstitutionId}` : '';

  document.getElementById('students-table-wrap').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading students...</div>';

  try {
    const resp = await fetch(`${DAZZLING_URL}/students${instQuery}`, { headers });
    const data = resp.ok ? await resp.json() : { students: [] };
    const students = data.students || [];

    if (!students.length) {
      document.getElementById('students-table-wrap').innerHTML =
        '<div class="loading">No students registered.</div>';
      return;
    }

    const rows = students.map(s => `
      <tr>
        <td>${escapeHtml(s.id || '—')}</td>
        <td>${escapeHtml(s.name || '—')}</td>
        <td>${escapeHtml(s.institution_id || '—')}</td>
        <td>
          <button class="btn-delete" onclick="openDeleteModal('${escapeJsString(s.id)}', '${escapeJsString(s.name || '')}')">Delete</button>
        </td>
      </tr>
    `).join('');

    document.getElementById('students-table-wrap').innerHTML = `
      <table>
        <thead><tr><th>Student ID</th><th>Name</th><th>Institution</th><th>Action</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="table-footer">${students.length} students</div>
    `;
  } catch (e) {
    document.getElementById('students-table-wrap').innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${escapeHtml(e.message)}</div>`;
  }
}

// ── Load coordinators ──────────────────────────────────────────────────────
async function loadCoordinators() {
  if (!currentToken) return;

  document.getElementById('team-table-wrap').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading team...</div>';

  try {
    const teamInstFilter = document.getElementById('filter-team-inst');
    const teamInstVal    = teamInstFilter ? teamInstFilter.value : '';
    const teamInstQuery  = teamInstVal ? `?institution_id=${teamInstVal}` : '';
    const resp = await fetch(`${DAZZLING_URL}/coordinators${teamInstQuery}`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      document.getElementById('team-table-wrap').innerHTML =
        `<div class="loading" style="color:var(--red)">${escapeHtml(err.detail || 'Failed to load team.')}</div>`;
      return;
    }

    const data = await resp.json();
    const coordinators = data.coordinators || [];
    coordinatorsData = coordinators;

    if (!coordinators.length) {
      document.getElementById('team-table-wrap').innerHTML = `
        <div class="loading" style="padding:48px;">
          <div style="margin-bottom:12px;font-size:1.5rem;">👥</div>
          No coordinators yet. Invite someone to get started.
        </div>
      `;
      return;
    }

    if (!isSuperAdmin && !courseUnitsCache.length && currentInstitutionId) {
      const { data: units, error } = await client
        .from('course_units').select('id, name, code')
        .eq('institution_id', currentInstitutionId).order('created_at', { ascending: true });
      if (!error) courseUnitsCache = units || [];
    }

    const rows = coordinators.map(c => {
      const joined   = c.created_at
        ? new Date(c.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
        : '—';
      const safeName = escapeJsString(c.full_name || '');
      const instCell = isSuperAdmin
        ? `<td style="color:var(--muted);font-size:0.8rem;">${escapeHtml(c.institution_id || '—')}</td>`
        : '';

      let assignedUnitIds = [];
      if (Array.isArray(c.course_unit_id)) assignedUnitIds = c.course_unit_id;
      else if (c.course_unit_id) assignedUnitIds = [c.course_unit_id];

      const assignedUnits = assignedUnitIds
        .map(id => courseUnitsCache.find(u => u.id == id)).filter(u => u)
        .map(u => `${escapeHtml(u.name)}${u.code ? ' (' + escapeHtml(u.code) + ')' : ''}`);

      const unitCell = !isSuperAdmin ? `<td>
            <select class="unit-assign-select" multiple id="unit-select-${c.id}">
              ${courseUnitsCache.map(u =>
                `<option value="${escapeAttr(u.id)}">${escapeHtml(u.name)}${u.code ? ' (' + escapeHtml(u.code) + ')' : ''}</option>`
              ).join('')}
            </select>
            <button onclick="assignCoordinatorUnit('${escapeJsString(c.id)}')"
              style="margin-top:6px;display:block;background:transparent;border:1px solid rgba(74,158,255,0.4);color:var(--blue);padding:4px 12px;border-radius:6px;font-size:0.75rem;cursor:pointer;transition:background 0.2s;"
              onmouseover="this.style.background='rgba(74,158,255,0.1)'"
              onmouseout="this.style.background='transparent'">Save</button>
           </td>` : '';

      return `
        <tr>
          <td>
            ${c.full_name ? escapeHtml(c.full_name) : '<span style="color:var(--muted)">Pending setup</span>'}
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;">
              ${assignedUnits.length > 0
                ? assignedUnits.map(u => `<span style="background:rgba(74,158,255,0.1);border:1px solid rgba(74,158,255,0.2);color:var(--blue);border-radius:100px;padding:2px 10px;font-size:0.68rem;font-weight:600;letter-spacing:0.05em;">${u}</span>`).join('')
                : '<span style="color:var(--muted);font-size:0.78rem;">No units assigned</span>'}
            </div>
          </td>
          <td><span class="badge badge-coord">Coordinator</span></td>
          ${instCell}${unitCell}
          <td style="color:var(--muted);font-size:0.8rem;">${joined}</td>
          <td><button class="btn-delete" onclick="openRemoveCoordModal('${escapeJsString(c.id)}', '${safeName}')">Remove</button></td>
        </tr>
      `;
    }).join('');

    const unitHeader = !isSuperAdmin ? '<th>Assign Units</th>' : '';
    document.getElementById('team-table-wrap').innerHTML = `
      <table>
        <thead>
          <tr><th>Name</th><th>Role</th>${isSuperAdmin ? '<th>Institution</th>' : ''}${unitHeader}<th>Added</th><th>Action</th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="table-footer">${coordinators.length} coordinator${coordinators.length !== 1 ? 's' : ''}</div>
    `;
  } catch (e) {
    document.getElementById('team-table-wrap').innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${escapeHtml(e.message)}</div>`;
  }
}

// ── LECTURER STATE ─────────────────────────────────────────────────────────
let lecturersData = [];
let pendingRemoveLecturerId = null;
let pendingRemoveLecturerName = null;
let pendingAssignLecturerId = null;

// ── LOAD LECTURERS ─────────────────────────────────────────────────────────
async function loadLecturers() {
  if (!currentToken) return;

  document.getElementById('lecturers-table-wrap').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading lecturers...</div>';

  try {
    // Load course units cache if not already loaded
    if (!isSuperAdmin && !courseUnitsCache.length && currentInstitutionId) {
      const { data: units, error } = await client
        .from('course_units').select('id, name, code')
        .eq('institution_id', currentInstitutionId)
        .order('created_at', { ascending: true });
      if (!error) courseUnitsCache = units || [];
    }

    const instQuery = !isSuperAdmin && currentInstitutionId
      ? `?institution_id=${encodeURIComponent(currentInstitutionId)}&role=lecturer`
      : `?role=lecturer`;

    const resp = await fetch(`${DAZZLING_URL}/lecturers${instQuery}`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    const data = resp.ok ? await resp.json() : null;
    console.log('[dashboard] loadLecturers: backend_response_ok=', resp.ok, 'status=', resp.status, 'body=', data);
    if (!resp.ok) {
      const err = data?.detail || data?.message || `HTTP ${resp.status}`;
      throw new Error(err);
    }

    lecturersData = Array.isArray(data) ? data : (data?.lecturers || []);
    console.log('[dashboard] loadLecturers: lecturers_found=', lecturersData.length);

    if (!lecturersData.length) {
      document.getElementById('lecturers-table-wrap').innerHTML = `
        <div class="loading" style="padding:48px;">
          <div style="margin-bottom:12px;font-size:1.5rem;">👨‍🏫</div>
          No lecturers yet. Invite someone to get started.
        </div>
      `;
      return;
    }

    // For each lecturer, fetch their assigned course units from lecturer_courses
    const lecturerIds = lecturersData.map(l => l.id);
    const { data: assignments } = await client
      .from('lecturer_courses')
      .select('lecturer_id, course_unit_id')
      .in('lecturer_id', lecturerIds);

    const assignmentMap = {};
    (assignments || []).forEach(a => {
      if (!assignmentMap[a.lecturer_id]) assignmentMap[a.lecturer_id] = [];
      assignmentMap[a.lecturer_id].push(a.course_unit_id);
    });

    const rows = lecturersData.map(l => {
      const joined = l.created_at
        ? new Date(l.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
        : '—';
      const safeName = escapeJsString(l.full_name || '');
      const instCell = isSuperAdmin
        ? `<td style="color:var(--muted);font-size:0.8rem;">${escapeHtml(l.institution_id || '—')}</td>`
        : '';

      const assignedUnitIds = assignmentMap[l.id] || [];
      const assignedUnits = assignedUnitIds
        .map(id => courseUnitsCache.find(u => u.id === id)).filter(u => u)
        .map(u => `${escapeHtml(u.name)}${u.code ? ' (' + escapeHtml(u.code) + ')' : ''}`);

      return `
        <tr>
          <td>
            ${l.full_name ? escapeHtml(l.full_name) : '<span style="color:var(--muted)">Pending setup</span>'}
            <div style="color:var(--muted);font-size:0.78rem;margin-top:2px;">${escapeHtml(l.email || '')}</div>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;">
              ${assignedUnits.length > 0
                ? assignedUnits.map(u =>
                    `<span style="background:rgba(74,158,255,0.1);border:1px solid rgba(74,158,255,0.2);color:var(--blue);border-radius:100px;padding:2px 10px;font-size:0.68rem;font-weight:600;letter-spacing:0.05em;">${u}</span>`
                  ).join('')
                : '<span style="color:var(--muted);font-size:0.78rem;">No units assigned</span>'
              }
            </div>
          </td>
          <td><span class="badge badge-coord" style="background:rgba(168,85,247,0.12);color:#a855f7;border-color:rgba(168,85,247,0.25);">Lecturer</span></td>
          ${instCell}
          <td>
            <button onclick="openAssignLecturerModal('${escapeJsString(l.id)}', '${safeName}')"
              style="background:transparent;border:1px solid rgba(74,158,255,0.4);color:var(--blue);padding:4px 12px;border-radius:6px;font-size:0.75rem;cursor:pointer;transition:background 0.2s;"
              onmouseover="this.style.background='rgba(74,158,255,0.1)'"
              onmouseout="this.style.background='transparent'">Assign Units</button>
          </td>
          <td style="color:var(--muted);font-size:0.8rem;">${joined}</td>
          <td><button class="btn-delete" onclick="openRemoveLecturerModal('${escapeJsString(l.id)}', '${safeName}')">Remove</button></td>
        </tr>
      `;
    }).join('');

    document.getElementById('lecturers-table-wrap').innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Role</th>
            ${isSuperAdmin ? '<th>Institution</th>' : ''}
            <th>Units</th>
            <th>Added</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="table-footer">${lecturersData.length} lecturer${lecturersData.length !== 1 ? 's' : ''}</div>
    `;
  } catch (e) {
    document.getElementById('lecturers-table-wrap').innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${escapeHtml(e.message)}</div>`;
  }
}

// ── INVITE LECTURER ────────────────────────────────────────────────────────
function openInviteLecturerModal() {
  document.getElementById('invite-lecturer-name').value = '';
  document.getElementById('invite-lecturer-email').value = '';
  document.getElementById('invite-lecturer-error').style.display = 'none';
  document.getElementById('send-lecturer-invite-btn').disabled = false;
  document.getElementById('send-lecturer-invite-btn').textContent = 'Send Invite';
  document.getElementById('invite-lecturer-modal').classList.add('visible');
}

function closeInviteLecturerModal() {
  document.getElementById('invite-lecturer-modal').classList.remove('visible');
}

async function sendLecturerInvite() {
  const nameEl  = document.getElementById('invite-lecturer-name');
  const emailEl = document.getElementById('invite-lecturer-email');
  const errEl   = document.getElementById('invite-lecturer-error');
  const btn     = document.getElementById('send-lecturer-invite-btn');
  const name    = nameEl.value.trim();
  const email   = emailEl.value.trim();

  errEl.style.display = 'none';
  if (!name)  { errEl.textContent = 'Please enter a full name.';     errEl.style.display = 'block'; return; }
  if (!email) { errEl.textContent = 'Please enter an email address.'; errEl.style.display = 'block'; return; }

  btn.disabled = true;
  btn.textContent = 'Sending...';

  try {
    const formData = new FormData();
    formData.append('full_name', name);
    formData.append('email', email);
    formData.append('role', 'lecturer');

    const resp = await fetch(`${DAZZLING_URL}/invite-coordinator`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${currentToken}` },
      body: formData,
    });

    const result = await resp.json();
    if (resp.ok) {
      closeInviteLecturerModal();
      showToast(result.message || `✓ Lecturer added: ${email}`, 'success');
      await loadLecturers();
    } else {
      errEl.textContent = result.detail || 'Invite failed. Please try again.';
      errEl.style.display = 'block';
      btn.disabled = false;
      btn.textContent = 'Send Invite';
    }
  } catch (e) {
    errEl.textContent = `Error: ${e.message}`;
    errEl.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Send Invite';
  }
}

// ── ASSIGN LECTURER TO UNITS ───────────────────────────────────────────────
function openAssignLecturerModal(lecturerId, lecturerName) {
  pendingAssignLecturerId = lecturerId;

  document.getElementById('assign-lecturer-modal-desc').textContent =
    `Select which course units ${lecturerName || 'this lecturer'} teaches.`;
  document.getElementById('assign-lecturer-error').style.display = 'none';

  // Populate unit select
  const select = document.getElementById('assign-lecturer-unit-select');
  select.innerHTML = courseUnitsCache.length
    ? courseUnitsCache.map(u =>
        `<option value="${escapeAttr(u.id)}">${escapeHtml(u.name)}${u.code ? ' (' + escapeHtml(u.code) + ')' : ''}</option>`
      ).join('')
    : '<option disabled>No course units found</option>';

  // Pre-select already assigned units
  const lecturer = lecturersData.find(l => l.id === lecturerId);
  if (lecturer) {
    // Get current assignments from the table rows (already loaded)
    const unitBadges = document.querySelectorAll(`#lecturers-table-wrap span[data-lid="${lecturerId}"]`);
    // Use the assignments loaded during loadLecturers
    client.from('lecturer_courses')
      .select('course_unit_id')
      .eq('lecturer_id', lecturerId)
      .then(({ data }) => {
        const assigned = (data || []).map(a => a.course_unit_id);
        Array.from(select.options).forEach(opt => {
          opt.selected = assigned.includes(opt.value);
        });
      });
  }

  document.getElementById('assign-lecturer-modal').classList.add('visible');
}

function closeAssignLecturerModal() {
  pendingAssignLecturerId = null;
  document.getElementById('assign-lecturer-modal').classList.remove('visible');
}

async function confirmAssignLecturer() {
  if (!pendingAssignLecturerId || !currentToken) return;

  const select = document.getElementById('assign-lecturer-unit-select');
  const selectedUnitIds = Array.from(select.options)
    .filter(o => o.selected)
    .map(o => o.value);

  const errEl = document.getElementById('assign-lecturer-error');
  const btn   = document.getElementById('confirm-assign-lecturer-btn');
  errEl.style.display = 'none';

  if (selectedUnitIds.length === 0) {
    errEl.textContent = 'Please select at least one course unit.';
    errEl.style.display = 'block';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Saving...';

  try {
    const lecturerId = pendingAssignLecturerId;

    // 1. Delete all existing assignments for this lecturer
    const { error: delError } = await client
      .from('lecturer_courses')
      .delete()
      .eq('lecturer_id', lecturerId);

    if (delError) throw delError;

    // 2. Assign each selected course unit via backend API
    const results = [];
    for (const unitId of selectedUnitIds) {
      const unitName = Array.from(select.options)
        .find(o => o.value === unitId)?.text || unitId;

      try {
        const formData = new FormData();
        formData.append('lecturer_id', lecturerId);
        formData.append('course_unit_id', unitId);
        if (currentInstitutionId) {
          formData.append('institution_id', currentInstitutionId);
        }

        const resp = await fetch(`${DAZZLING_URL}/admin/lecturer-courses`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${currentToken}` },
          body: formData,
        });

        const result = await resp.json();
        if (resp.ok) {
          results.push({ unit: unitName, success: true });
        } else {
          results.push({ unit: unitName, success: false, error: result.detail || 'Unknown error' });
        }
      } catch (e) {
        results.push({ unit: unitName, success: false, error: e.message });
      }
    }

    // 3. Show detailed feedback
    const successCount = results.filter(r => r.success).length;
    const failedCount = results.filter(r => !r.success).length;

    if (failedCount === 0) {
      closeAssignLecturerModal();
      showToast(`✓ ${successCount} course unit${successCount !== 1 ? 's' : ''} assigned successfully`, 'success');
    } else {
      const failedUnits = results.filter(r => !r.success).map(r => r.unit).join(', ');
      errEl.innerHTML = `<strong>Partial success:</strong> ${successCount} assigned, ${failedCount} failed.<br>Failed units: ${escapeHtml(failedUnits)}`;
      errEl.style.display = 'block';
      btn.disabled = false;
      btn.textContent = 'Save';
      
      if (successCount > 0) {
        showToast(`⚠ ${successCount} assigned, ${failedCount} failed`, 'error');
      }
    }

    await loadLecturers();
  } catch (e) {
    errEl.textContent = `Failed: ${e.message}`;
    errEl.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Save';
  }
}

// ── REMOVE LECTURER ────────────────────────────────────────────────────────
function openRemoveLecturerModal(lecturerId, lecturerName) {
  pendingRemoveLecturerId   = lecturerId;
  pendingRemoveLecturerName = lecturerName;
  document.getElementById('remove-lecturer-modal-msg').textContent =
    `Are you sure you want to remove ${lecturerName || 'this lecturer'}? They will lose access immediately.`;
  document.getElementById('remove-lecturer-modal').classList.add('visible');
}

function closeRemoveLecturerModal() {
  pendingRemoveLecturerId   = null;
  pendingRemoveLecturerName = null;
  document.getElementById('remove-lecturer-modal').classList.remove('visible');
}

async function confirmRemoveLecturer() {
  if (!pendingRemoveLecturerId || !currentToken) return;
  const lecturerId = pendingRemoveLecturerId;
  closeRemoveLecturerModal();

  try {
    // 1. Remove lecturer_courses assignments first
    await client
      .from('lecturer_courses')
      .delete()
      .eq('lecturer_id', lecturerId);

    // 2. Delete profile via existing coordinator delete endpoint
    const resp = await fetch(`${DAZZLING_URL}/coordinators/${lecturerId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${currentToken}` },
    });

    if (resp.ok) {
      showToast('Lecturer removed', 'success');
      await loadLecturers();
    } else {
      const err = await resp.json().catch(() => ({}));
      showToast(`Failed: ${err.detail || 'Unknown error'}`, 'error');
    }
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
  }
}

// ── COURSE UNITS ───────────────────────────────────────────────────────────
async function loadCourseUnits() {
  if (!currentToken || !currentInstitutionId) return;
  document.getElementById('units-table-wrap').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading course units...</div>';

  try {
    const { data: units, error } = await client
      .from('course_units').select('id, name, code, created_at')
      .eq('institution_id', currentInstitutionId).order('created_at', { ascending: true });
    if (error) throw error;
    courseUnitsCache = units || [];

    if (!courseUnitsCache.length) {
      document.getElementById('units-table-wrap').innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📚</div>
          <p>No course units yet.<br>Add your first unit above.</p>
        </div>`;
      return;
    }

    const rows = courseUnitsCache.map(u => {
      const created = new Date(u.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
      return `<tr>
        <td><strong>${escapeHtml(u.name)}</strong></td>
        <td style="color:var(--muted)">${escapeHtml(u.code || '—')}</td>
        <td style="color:var(--muted);font-size:0.78rem;">${created}</td>
        <td><button class="btn-delete" onclick="deleteCourseUnit('${escapeJsString(u.id)}', '${escapeJsString(u.name)}')">Delete</button></td>
      </tr>`;
    }).join('');

    document.getElementById('units-table-wrap').innerHTML = `
      <table>
        <thead><tr><th>Unit Name</th><th>Code</th><th>Created</th><th>Action</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="table-footer">${courseUnitsCache.length} unit${courseUnitsCache.length !== 1 ? 's' : ''}</div>
    `;
  } catch (e) {
    document.getElementById('units-table-wrap').innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${e.message}</div>`;
  }
}

// ── DEPARTMENTS ────────────────────────────────────────────────────────────
async function loadDepartments() {
  if (!currentToken) return;
  document.getElementById('departments-table-wrap').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading departments...</div>';

  try {
    const instQuery = currentInstitutionId ? `?institution_id=${encodeURIComponent(currentInstitutionId)}` : '';
    const resp = await fetch(`${DAZZLING_URL}/departments${instQuery}`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    const data = await resp.json();
    const departments = data.departments || [];

    if (!departments.length) {
      document.getElementById('departments-table-wrap').innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🏛️</div>
          <p>No departments yet.<br>Add your first department above.</p>
        </div>`;
      return;
    }

    const rows = departments.map(d => {
      const created = d.created_at
        ? new Date(d.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
        : '—';
      return `<tr>
        <td><strong>${escapeHtml(d.name)}</strong></td>
        <td style="color:var(--muted);font-size:0.78rem;">${created}</td>
        <td><button class="btn-delete" onclick="deleteDepartment('${escapeJsString(d.id)}', '${escapeJsString(d.name)}')">Delete</button></td>
      </tr>`;
    }).join('');

    document.getElementById('departments-table-wrap').innerHTML = `
      <table>
        <thead><tr><th>Department Name</th><th>Created</th><th>Action</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="table-footer">${departments.length} department${departments.length !== 1 ? 's' : ''}</div>
    `;
  } catch (e) {
    document.getElementById('departments-table-wrap').innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${e.message}</div>`;
  }
}

// ── DEPT ADMINS ────────────────────────────────────────────────────────────
async function loadDeptAdmins() {
  if (!currentToken) return;
  document.getElementById('deptadmins-table-wrap').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading department admins...</div>';

  try {
    const instQuery = currentInstitutionId ? `?institution_id=${encodeURIComponent(currentInstitutionId)}` : '';
    const resp = await fetch(`${DAZZLING_URL}/dept-admins${instQuery}`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    const data = await resp.json();
    const profiles = data.dept_admins || [];

    if (!profiles.length) {
      document.getElementById('deptadmins-table-wrap').innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">👤</div>
          <p>No department admins yet.<br>Invite your first dept admin above.</p>
        </div>`;
      return;
    }

    const rows = profiles.map(p => {
      const created = p.created_at
        ? new Date(p.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
        : '—';
      return `<tr>
        <td><strong>${escapeHtml(p.full_name || '—')}</strong></td>
        <td style="color:var(--muted)">${escapeHtml(p.email || '—')}</td>
        <td style="color:var(--muted);font-size:0.78rem;">${created}</td>
        <td><button class="btn-delete" onclick="removeDeptAdmin('${escapeJsString(p.id)}', '${escapeJsString(p.full_name)}')">Remove</button></td>
      </tr>`;
    }).join('');

    document.getElementById('deptadmins-table-wrap').innerHTML = `
      <table>
        <thead><tr><th>Name</th><th>Email</th><th>Created</th><th>Action</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="table-footer">${profiles.length} admin${profiles.length !== 1 ? 's' : ''}</div>
    `;
  } catch (e) {
    document.getElementById('deptadmins-table-wrap').innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${e.message}</div>`;
  }
}

async function createCourseUnit() {
  const nameEl = document.getElementById('unit-name-input');
  const codeEl = document.getElementById('unit-code-input');
  const errEl  = document.getElementById('units-create-error');
  const btn    = document.getElementById('add-unit-btn');
  const name   = nameEl.value.trim();
  const code   = codeEl.value.trim();
  errEl.style.display = 'none';
  if (!name) { errEl.textContent = 'Unit name is required.'; errEl.style.display = 'block'; return; }
  btn.disabled = true; btn.textContent = 'Adding...';
  try {
    const { error } = await client.from('course_units')
      .insert({ institution_id: currentInstitutionId, name, code: code || null });
    if (error) throw error;
    nameEl.value = ''; codeEl.value = '';
    showToast(`✓ "${name}" added`, 'success');
    await loadCourseUnits(); populateInviteUnitDropdown(); populateAIScopeUnits();
  } catch (e) { errEl.textContent = e.message || 'Failed to create unit.'; errEl.style.display = 'block'; }
  finally { btn.disabled = false; btn.textContent = '+ Add Unit'; }
}

async function deleteCourseUnit(unitId, unitName) {
  if (!confirm(`Delete "${unitName}"? Coordinators assigned to it will become unassigned.`)) return;
  try {
    const { error } = await client.from('course_units').delete().eq('id', unitId);
    if (error) throw error;
    showToast(`"${unitName}" deleted`, 'success');
    await loadCourseUnits(); populateInviteUnitDropdown(); populateAIScopeUnits();
  } catch (e) { showToast(`Failed: ${e.message}`, 'error'); }
}

async function assignCoordinatorUnit(coordId) {
  const selectElement = document.getElementById(`unit-select-${coordId}`);
  if (!selectElement) return;
  const newUnitIds = Array.from(selectElement.selectedOptions).map(o => o.value).filter(id => id);
  if (!newUnitIds.length) { showToast('Select at least one unit first', 'error'); return; }
  const coord = coordinatorsData.find(c => c.id === coordId);
  let existing = Array.isArray(coord?.course_unit_id) ? coord.course_unit_id : coord?.course_unit_id ? [coord.course_unit_id] : [];
  const merged = [...new Set([...existing, ...newUnitIds])];
  try {
    const body = new URLSearchParams();
    body.append('course_unit_ids', merged.join(','));
    const resp = await fetch(`${DAZZLING_URL}/admin/coordinators/${coordId}/course-unit`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${currentToken}`, 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
    const result = await resp.json();
    if (!resp.ok) throw new Error(result.detail || 'Failed to update.');
    const unitNames = Array.from(selectElement.selectedOptions).map(o => o.text).join(', ');
    showToast(`✓ Assigned: ${unitNames}`, 'success');
    await loadCoordinators();
  } catch (e) { showToast(`Failed: ${e.message}`, 'error'); await loadCoordinators(); }
}

function populateInviteUnitDropdown() {
  const sel = document.getElementById('invite-unit');
  if (!sel) return;
  sel.innerHTML = '<option value="">— Select a unit —</option>' +
    courseUnitsCache.map(u => `<option value="${u.id}">${u.name}${u.code ? ' (' + u.code + ')' : ''}</option>`).join('');
}

// ── Load analytics ────────────────────────────────────────────────────────
async function loadAnalytics() {
  if (!currentToken || !isSuperAdmin) return;

  document.getElementById('analytics-wrap').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading analytics...</div>';

  try {
    const [revenue, churn, usage, payments] = await Promise.all([
      fetch(`${DAZZLING_URL}/admin/analytics/revenue`, { headers: { 'Authorization': `Bearer ${currentToken}` } }).then(r => r.json()),
      fetch(`${DAZZLING_URL}/admin/analytics/churn`, { headers: { 'Authorization': `Bearer ${currentToken}` } }).then(r => r.json()),
      fetch(`${DAZZLING_URL}/admin/analytics/usage`, { headers: { 'Authorization': `Bearer ${currentToken}` } }).then(r => r.json()),
      fetch(`${DAZZLING_URL}/admin/analytics/payments`, { headers: { 'Authorization': `Bearer ${currentToken}` } }).then(r => r.json()),
    ]);

    const planRows = Object.entries(revenue.plan_breakdown || {}).map(([plan, data]) =>
      `<tr><td style="text-transform:capitalize;">${escapeHtml(plan)}</td><td>${data.count}</td><td>KES ${data.mrr.toLocaleString()}</td></tr>`
    ).join('');

    const usageRows = (usage || []).map(u =>
      `<tr>
        <td>${escapeHtml(u.institution)}</td>
        <td style="text-transform:capitalize;">${escapeHtml(u.plan)}</td>
        <td>${u.students} / ${u.limit === 999999 ? '∞' : u.limit}</td>
        <td>
          <div style="background:var(--border);border-radius:4px;height:6px;width:100px;display:inline-block;vertical-align:middle;">
            <div style="background:var(--cyan);height:6px;border-radius:4px;width:${Math.min(u.utilization,100)}%;"></div>
          </div>
          <span style="margin-left:8px;color:var(--muted);font-size:0.8rem;">${u.utilization}%</span>
        </td>
      </tr>`
    ).join('');

    document.getElementById('analytics-wrap').innerHTML = `
      <div class="analytics-metrics-grid">
        <div class="metric-card">
          <div class="metric-label">MRR</div>
          <div class="metric-value">KES ${(revenue.mrr||0).toLocaleString()}</div>
          <div class="metric-sub">ARR: KES ${(revenue.arr||0).toLocaleString()}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Total Institutions</div>
          <div class="metric-value">${revenue.total_institutions||0}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Churn Rate</div>
          <div class="metric-value">${churn.churn_rate||0}%</div>
          <div class="metric-sub">${churn.churned_count} churned in ${churn.period_days}d</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Payment Success</div>
          <div class="metric-value">${payments.success_rate||0}%</div>
          <div class="metric-sub">${payments.successful||0} / ${payments.total_payments||0} payments</div>
        </div>
      </div>
      <h3 style="margin:24px 0 12px;font-size:0.95rem;">Plan Breakdown</h3>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Plan</th><th>Institutions</th><th>MRR</th></tr></thead>
          <tbody>${planRows}</tbody>
        </table>
      </div>
      <h3 style="margin:24px 0 12px;font-size:0.95rem;">Institution Usage</h3>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Institution</th><th>Plan</th><th>Students</th><th>Utilization</th></tr></thead>
          <tbody>${usageRows}</tbody>
        </table>
      </div>
    `;
  } catch (e) {
    document.getElementById('analytics-wrap').innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${escapeHtml(e.message)}</div>`;
  }
}

// ── Load billing ───────────────────────────────────────────────────────────
async function loadBilling() {
  document.getElementById('billing-wrap').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading billing info...</div>';
  try {
    const resp = await fetch(`/check-trial/${currentInstitutionId}`);
    const inst = await resp.json();
    const plan     = inst.plans || 'trial';
    const daysLeft = inst.days_left ?? null;

    const planLabels = {
      trial:      'Free Trial',
      starter:    'Starter — $49/mo',
      growth:     'Growth — $99/mo',
      pro:        'Pro — $199/mo',
      enterprise: 'Enterprise',
    };

    const trialBlock = plan === 'trial' ? `
      <div class="billing-card orange">
        <div class="metric-label">Trial Status</div>
        <div class="metric-value">${daysLeft !== null && daysLeft > 0 ? `${daysLeft} day${daysLeft !== 1 ? 's' : ''} left` : 'Expired'}</div>
        <div class="metric-sub" style="margin-top:8px;">${daysLeft > 0 ? `${daysLeft} day${daysLeft !== 1 ? 's' : ''} remaining` : 'Expired — upgrade to restore access'}</div>
      </div>` : '';

    let upgradeBlock = '';

    if (plan === 'trial' || plan === 'starter') {
      upgradeBlock = `
        <div class="upgrade-section">
          <div class="upgrade-title">Upgrade Your Plan</div>
          <div class="upgrade-desc">Choose a plan that fits your institution size. All plans include the full FaceAttend feature set.</div>
          <div class="upgrade-plans-grid">
            <div class="upgrade-plan-card${plan === 'starter' ? ' current' : ''}">
              <div class="upgrade-plan-name">Starter</div>
              <div class="upgrade-plan-price">$49<span>/mo</span></div>
              <div class="upgrade-plan-limit">Up to 500 students</div>
              ${plan === 'starter'
                ? '<div class="upgrade-plan-current">Current plan</div>'
                : '<button onclick="handleUpgrade(\'starter\')" class="btn-upgrade">Pay Now</button>'}
            </div>
            <div class="upgrade-plan-card featured${plan === 'growth' ? ' current' : ''}">
              <div class="upgrade-plan-badge">Most Popular</div>
              <div class="upgrade-plan-name">Growth</div>
              <div class="upgrade-plan-price">$99<span>/mo</span></div>
              <div class="upgrade-plan-limit">Up to 2,000 students</div>
              ${plan === 'growth'
                ? '<div class="upgrade-plan-current">Current plan</div>'
                : '<button onclick="handleUpgrade(\'growth\')" class="btn-upgrade btn-upgrade--featured">Pay Now</button>'}
            </div>
            <div class="upgrade-plan-card${plan === 'pro' ? ' current' : ''}">
              <div class="upgrade-plan-name">Pro</div>
              <div class="upgrade-plan-price">$199<span>/mo</span></div>
              <div class="upgrade-plan-limit">Up to 5,000 students</div>
              ${plan === 'pro'
                ? '<div class="upgrade-plan-current">Current plan</div>'
                : '<button onclick="handleUpgrade(\'pro\')" class="btn-upgrade">Pay Now</button>'}
            </div>
          </div>
          <div class="pesapal-note">Secure payment via Pesapal · MTN MoMo, Airtel Money, cards &amp; bank transfer</div>
          <div style="margin-top:16px;font-size:0.82rem;color:var(--muted);">
            Need 5,000+ students or multi-campus support?
            <a href="mailto:admin@faceattend.app?subject=Enterprise Plan" style="color:var(--cyan);">Contact us for Enterprise pricing →</a>
          </div>
        </div>`;
    } else if (plan === 'growth') {
      upgradeBlock = `
        <div class="upgrade-section">
          <p>You're on the <strong>Growth plan</strong> (up to 2,000 students).</p>
          <p style="margin-top:8px;">Need more capacity? <button onclick="handleUpgrade('pro')" class="btn-upgrade" style="display:inline-block;width:auto;padding:8px 20px;margin-left:8px;">Upgrade to Pro — $199/mo</button></p>
          <div style="margin-top:16px;font-size:0.82rem;color:var(--muted);">
            Need 5,000+ students? <a href="mailto:admin@faceattend.app?subject=Enterprise Plan" style="color:var(--cyan);">Contact us for Enterprise →</a>
          </div>
        </div>`;
    } else if (plan === 'pro') {
      upgradeBlock = `
        <div class="upgrade-section">
          <p>You're on the <strong>Pro plan</strong> (up to 5,000 students).</p>
          <div style="margin-top:12px;font-size:0.82rem;color:var(--muted);">
            Need 5,000+ students or multi-campus support? <a href="mailto:admin@faceattend.app?subject=Enterprise Plan" style="color:var(--cyan);">Contact us for Enterprise →</a>
          </div>
        </div>`;
    } else if (plan === 'enterprise') {
      upgradeBlock = `
        <div class="upgrade-section">
          <p style="color:var(--purple);">You're on the <strong>Enterprise plan</strong>.</p>
          <p style="margin-top:8px;font-size:0.85rem;color:var(--muted);">For billing inquiries or changes, contact us directly.</p>
          <button class="btn-contact-enterprise" onclick="window.open('mailto:admin@faceattend.app?subject=Enterprise Billing','_blank')">Contact Support</button>
        </div>`;
    }

    document.getElementById('billing-wrap').innerHTML = `
      <div class="billing-grid">
        <div class="billing-card cyan">
          <div class="metric-label">Current Plan</div>
          <div class="metric-value">${planLabels[plan] || plan}</div>
        </div>
        ${trialBlock}
      </div>
      ${upgradeBlock}`;
  } catch (e) {
    document.getElementById('billing-wrap').innerHTML =
      '<div class="loading" style="color:var(--red)">Failed to load billing info.</div>';
  }
}

async function handleUpgrade(plan) {
  const { data: { user } } = await client.auth.getUser();
  if (!user) return alert('Please log in first.');

  const { data: profile } = await client
    .from('profiles')
    .select('full_name, institution_id')
    .eq('id', user.id)
    .single();

  const nameParts = (profile?.full_name || 'User Name').split(' ');

  try {
    const resp = await fetch('/api/cart/create-cart', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plan,
        email:          user.email,
        first_name:     nameParts[0] || 'User',
        last_name:      nameParts[1] || 'Name',
        phone:          '',
        institution_id: profile?.institution_id || '',
      }),
    });
    const data = await resp.json();
    if (data.redirect_url) {
      window.location.href = data.redirect_url;
    } else {
      alert('Payment initiation failed: ' + (data.detail || JSON.stringify(data)));
    }
  } catch (e) {
    alert('Something went wrong. Please try again or contact admin@faceattend.app');
  }
}

// ── API KEYS ───────────────────────────────────────────────────────────────
// ── DEPARTMENTS & DEPT ADMINS STATE ───────────────────────────────────────
let departmentsCache         = [];
let deptAdminsData           = [];
let pendingRemoveDeptAdminId   = null;
let pendingRemoveDeptAdminName = null;

// ══════════════════════════════════════════════════════════════════════════
// DEPARTMENTS (REMOVED - using backend API version at line ~1753)
// ══════════════════════════════════════════════════════════════════════════
// This duplicate function has been removed. The active loadDepartments() 
// function now calls the backend /departments endpoint instead of 
// querying Supabase directly.

async function createDepartment() {
  const nameEl = document.getElementById('dept-name-input');
  const errEl  = document.getElementById('dept-create-error');
  const btn    = document.getElementById('add-dept-btn');
  const name   = nameEl.value.trim();

  errEl.style.display = 'none';
  if (!name) {
    errEl.textContent   = 'Department name is required.';
    errEl.style.display = 'block';
    return;
  }

  btn.disabled    = true;
  btn.textContent = 'Adding...';

  try {
    const formData = new FormData();
    formData.append('name', name);
    if (currentInstitutionId) {
      formData.append('institution_id', currentInstitutionId);
    }

    const resp = await fetch(`${DAZZLING_URL}/departments`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${currentToken}` },
      body: formData,
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    const result = await resp.json();
    nameEl.value = '';
    showToast(result.message || `✓ "${name}" added`, 'success');
    await loadDepartments();
  } catch (e) {
    errEl.textContent   = e.message || 'Failed to create department.';
    errEl.style.display = 'block';
  } finally {
    btn.disabled    = false;
    btn.textContent = '+ Add Department';
  }
}

async function deleteDepartment(deptId, deptName) {
  if (!confirm(`Delete "${deptName}"? Department admins assigned to it will become unassigned.`)) return;

  try {
    const resp = await fetch(`${DAZZLING_URL}/departments/${deptId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${currentToken}` },
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    const result = await resp.json();
    showToast(result.message || `"${deptName}" deleted`, 'success');
    await loadDepartments();
  } catch (e) {
    showToast(`Failed: ${e.message}`, 'error');
  }
}

// ══════════════════════════════════════════════════════════════════════════
// DEPT ADMINS (REMOVED - using backend API version at line ~1796)
// ══════════════════════════════════════════════════════════════════════════
// This duplicate function has been removed. The active loadDeptAdmins() 
// function now calls the backend /dept-admins endpoint instead of 
// querying Supabase directly.

// ── Invite Dept Admin ──────────────────────────────────────────────────────
function populateDeptAdminDeptDropdown() {
  const sel = document.getElementById('invite-deptadmin-dept');
  if (!sel) return;
  sel.innerHTML = '<option value="">— Select a department —</option>' +
    departmentsCache.map(d =>
      `<option value="${escapeAttr(d.id)}">${escapeHtml(d.name)}</option>`
    ).join('');
}

function openInviteDeptAdminModal() {
  document.getElementById('invite-deptadmin-name').value  = '';
  document.getElementById('invite-deptadmin-email').value = '';
  document.getElementById('invite-deptadmin-error').style.display = 'none';
  document.getElementById('send-deptadmin-invite-btn').disabled   = false;
  document.getElementById('send-deptadmin-invite-btn').textContent = 'Send Invite';

  // Load departments into dropdown via backend API
  if (!departmentsCache.length) {
    const instQuery = currentInstitutionId ? `?institution_id=${encodeURIComponent(currentInstitutionId)}` : '';
    fetch(`${DAZZLING_URL}/departments${instQuery}`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    })
      .then(r => r.json())
      .then(data => {
        departmentsCache = data.departments || [];
        populateDeptAdminDeptDropdown();
      })
      .catch(() => {
        departmentsCache = [];
        populateDeptAdminDeptDropdown();
      });
  } else {
    populateDeptAdminDeptDropdown();
  }

  document.getElementById('invite-deptadmin-modal').classList.add('visible');
  setTimeout(() => document.getElementById('invite-deptadmin-name').focus(), 100);
}

function closeInviteDeptAdminModal() {
  document.getElementById('invite-deptadmin-modal').classList.remove('visible');
}

async function sendDeptAdminInvite() {
  const nameEl  = document.getElementById('invite-deptadmin-name');
  const emailEl = document.getElementById('invite-deptadmin-email');
  const deptEl  = document.getElementById('invite-deptadmin-dept');
  const errEl   = document.getElementById('invite-deptadmin-error');
  const btn     = document.getElementById('send-deptadmin-invite-btn');
  const name    = nameEl.value.trim();
  const email   = emailEl.value.trim();
  const deptId  = deptEl.value;

  errEl.style.display = 'none';
  if (!name)  { errEl.textContent = 'Please enter a full name.';     errEl.style.display = 'block'; return; }
  if (!email) { errEl.textContent = 'Please enter an email address.'; errEl.style.display = 'block'; return; }

  btn.disabled    = true;
  btn.textContent = 'Sending...';

  try {
    const formData = new FormData();
    formData.append('full_name', name);
    formData.append('email', email);
    formData.append('role', 'dept_admin');

    const resp = await fetch(`${DAZZLING_URL}/invite-coordinator`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${currentToken}` },
      body: formData,
    });

    const result = await resp.json();

    if (resp.ok) {
      // If a department was selected, update their profile with department_id
      if (deptId && result.invited_id) {
        await client
          .from('profiles')
          .update({ department_id: deptId })
          .eq('id', result.invited_id);
      }

      closeInviteDeptAdminModal();
      showToast(`✓ Invite sent to ${email}`, 'success');
      await loadDeptAdmins();
    } else {
      errEl.textContent   = result.detail || 'Invite failed. Please try again.';
      errEl.style.display = 'block';
      btn.disabled        = false;
      btn.textContent     = 'Send Invite';
    }
  } catch (e) {
    errEl.textContent   = `Error: ${e.message}`;
    errEl.style.display = 'block';
    btn.disabled        = false;
    btn.textContent     = 'Send Invite';
  }
}

// ── Remove Dept Admin ──────────────────────────────────────────────────────
function openRemoveDeptAdminModal(adminId, adminName) {
  pendingRemoveDeptAdminId   = adminId;
  pendingRemoveDeptAdminName = adminName;
  document.getElementById('remove-deptadmin-modal-msg').textContent =
    `Are you sure you want to remove ${adminName || 'this admin'}? They will lose access immediately.`;
  document.getElementById('remove-deptadmin-modal').classList.add('visible');
}

function closeRemoveDeptAdminModal() {
  pendingRemoveDeptAdminId   = null;
  pendingRemoveDeptAdminName = null;
  document.getElementById('remove-deptadmin-modal').classList.remove('visible');
}

async function confirmRemoveDeptAdmin() {
  if (!pendingRemoveDeptAdminId || !currentToken) return;
  const adminId = pendingRemoveDeptAdminId;
  closeRemoveDeptAdminModal();

  try {
    const resp = await fetch(`${DAZZLING_URL}/coordinators/${adminId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${currentToken}` },
    });

    if (resp.ok) {
      showToast('Department admin removed', 'success');
      await loadDeptAdmins();
    } else {
      const err = await resp.json().catch(() => ({}));
      showToast(`Failed: ${err.detail || 'Unknown error'}`, 'error');
    }
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
  }
}


async function loadApiKeys() {
  if (!currentToken) return;
  document.getElementById('apikeys-table-wrap').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading keys...</div>';
  try {
    const orgId = currentInstitutionId;
    const query = orgId ? `?org_id=${orgId}` : '';
    const resp = await fetch(`${DAZZLING_URL}/v1/keys${query}`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      document.getElementById('apikeys-table-wrap').innerHTML =
        `<div class="loading" style="color:var(--red)">${err.detail || 'Failed to load API keys.'}</div>`;
      return;
    }
    const data = await resp.json();
    const keys = data.keys || [];
    if (!keys.length) {
      document.getElementById('apikeys-table-wrap').innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🔑</div>
          <p>No API keys yet.<br>Generate your first key to start using the FaceAttend Enterprise API.</p>
        </div>`;
      return;
    }
    const rows = keys.map(k => {
      const created  = k.created_at ? new Date(k.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '—';
      const lastUsed = k.last_used_at ? new Date(k.last_used_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : 'Never';
      const planBadge = k.plan === 'enterprise' ? '<span class="badge badge-enterprise">Enterprise</span>' :
        k.plan === 'pro' ? '<span class="badge badge-pro">Pro</span>' : '<span class="badge badge-starter">Starter</span>';
      const statusBadge = k.is_active ? '<span class="badge badge-active">Active</span>' : '<span class="badge badge-revoked">Revoked</span>';
      const revokeBtn = k.is_active
        ? `<button class="btn-revoke" onclick="openRevokeModal('${k.id}', '${(k.name || '').replace(/'/g, "\\'")}')">Revoke</button>`
        : `<span style="color:var(--muted);font-size:0.75rem;">—</span>`;
      const instCell = isSuperAdmin ? `<td style="color:var(--muted);font-size:0.78rem;">${k.org_id || '—'}</td>` : '';
      const suffix = k.key_suffix || '????';
      return `<tr>
        <td><strong>${k.name || 'Unnamed Key'}</strong></td>
        <td><span class="key-masked">fa_live_••••••••••••${suffix}</span></td>
        <td>${planBadge}</td><td>${statusBadge}</td>${instCell}
        <td class="last-used-cell">${lastUsed}</td>
        <td style="color:var(--muted);font-size:0.78rem;">${created}</td>
        <td>${revokeBtn}</td>
      </tr>`;
    }).join('');
    document.getElementById('apikeys-table-wrap').innerHTML = `
      <table>
        <thead><tr><th>Name</th><th>Key</th><th>Plan</th><th>Status</th>${isSuperAdmin ? '<th>Org</th>' : ''}<th>Last Used</th><th>Created</th><th>Action</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="table-footer">${keys.length} key${keys.length !== 1 ? 's' : ''}</div>`;
  } catch (e) {
    document.getElementById('apikeys-table-wrap').innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${e.message}</div>`;
  }
}

function openGenKeyModal() {
  document.getElementById('genkey-name').value = '';
  document.getElementById('genkey-error').style.display = 'none';
  document.getElementById('confirm-gen-btn').disabled = false;
  document.getElementById('confirm-gen-btn').textContent = 'Generate';
  document.getElementById('genkey-modal').classList.add('visible');
  setTimeout(() => document.getElementById('genkey-name').focus(), 100);
}
function closeGenKeyModal() { document.getElementById('genkey-modal').classList.remove('visible'); }

async function confirmGenerateKey() {
  const nameEl = document.getElementById('genkey-name');
  const errEl  = document.getElementById('genkey-error');
  const btn    = document.getElementById('confirm-gen-btn');
  const name   = nameEl.value.trim();
  errEl.style.display = 'none';
  if (!name) { errEl.textContent = 'Please enter a name.'; errEl.style.display = 'block'; return; }
  btn.disabled = true; btn.textContent = 'Generating...';
  try {
    const resp = await fetch(`${DAZZLING_URL}/v1/keys`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${currentToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    const result = await resp.json();
    if (resp.ok && result.api_key) {
      newKeyRawValue = result.api_key;
      closeGenKeyModal();
      const banner = document.getElementById('new-key-banner');
      document.getElementById('new-key-value').textContent = result.api_key;
      document.getElementById('copy-key-btn').textContent = 'Copy';
      document.getElementById('copy-key-btn').classList.remove('copied');
      banner.classList.add('visible');
      banner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      showToast('✓ API key generated', 'success');
      await loadApiKeys();
    } else {
      errEl.textContent = result.detail || 'Failed to generate key.'; errEl.style.display = 'block';
      btn.disabled = false; btn.textContent = 'Generate';
    }
  } catch (e) {
    errEl.textContent = `Error: ${e.message}`; errEl.style.display = 'block';
    btn.disabled = false; btn.textContent = 'Generate';
  }
}

function copyNewKey() {
  if (!newKeyRawValue) return;
  navigator.clipboard.writeText(newKeyRawValue).then(() => {
    const btn = document.getElementById('copy-key-btn');
    btn.textContent = '✓ Copied'; btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2500);
  }).catch(() => {
    const el = document.createElement('textarea');
    el.value = newKeyRawValue; el.style.position = 'fixed'; el.style.opacity = '0';
    document.body.appendChild(el); el.select(); document.execCommand('copy'); document.body.removeChild(el);
    const btn = document.getElementById('copy-key-btn');
    btn.textContent = '✓ Copied'; btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2500);
  });
}

function openRevokeModal(keyId, keyName) {
  pendingRevokeKeyId = keyId; pendingRevokeKeyName = keyName;
  document.getElementById('revoke-modal-msg').textContent =
    `Are you sure you want to revoke "${keyName || 'this key'}"? This cannot be undone.`;
  document.getElementById('revoke-modal').classList.add('visible');
}
function closeRevokeModal() {
  pendingRevokeKeyId = null; pendingRevokeKeyName = null;
  document.getElementById('revoke-modal').classList.remove('visible');
}
async function confirmRevoke() {
  if (!pendingRevokeKeyId || !currentToken) return;
  const keyId = pendingRevokeKeyId; closeRevokeModal();
  try {
    const resp = await fetch(`${DAZZLING_URL}/v1/keys/${keyId}`, {
      method: 'DELETE', headers: { 'Authorization': `Bearer ${currentToken}` },
    });
    if (resp.ok) { showToast('API key revoked', 'success'); await loadApiKeys(); }
    else { const err = await resp.json().catch(() => ({})); showToast(`Failed: ${err.detail || 'Unknown error'}`, 'error'); }
  } catch (e) { showToast(`Error: ${e.message}`, 'error'); }
}

function openInviteModal() {
  document.getElementById('invite-name').value  = '';
  document.getElementById('invite-email').value = '';
  document.getElementById('invite-error').style.display = 'none';
  document.getElementById('send-invite-btn').disabled   = false;
  document.getElementById('send-invite-btn').textContent = 'Send Invite';
  populateInviteUnitDropdown();
  document.getElementById('invite-unit').value = '';
  document.getElementById('invite-modal').classList.add('visible');
  setTimeout(() => document.getElementById('invite-name').focus(), 100);
}
function closeInviteModal() { document.getElementById('invite-modal').classList.remove('visible'); }

async function sendInvite() {
  const nameEl  = document.getElementById('invite-name');
  const emailEl = document.getElementById('invite-email');
  const unitEl  = document.getElementById('invite-unit');
  const errEl   = document.getElementById('invite-error');
  const btn     = document.getElementById('send-invite-btn');
  const name    = nameEl.value.trim();
  const email   = emailEl.value.trim();
  const unitId  = unitEl.value;
  errEl.style.display = 'none';
  if (!name)  { showInviteError('Please enter a full name.'); return; }
  if (!email) { showInviteError('Please enter an email address.'); return; }
  btn.disabled = true; btn.textContent = 'Sending...';
  try {
    const formData = new FormData();
    formData.append('full_name', name); formData.append('email', email);
    if (unitId) formData.append('course_unit_id', unitId);
    const resp = await fetch(`${DAZZLING_URL}/invite-coordinator`, {
      method: 'POST', headers: { 'Authorization': `Bearer ${currentToken}` }, body: formData,
    });
    const result = await resp.json();
    if (resp.ok) { closeInviteModal(); showToast(`✓ Invite sent to ${email}`, 'success'); await loadCoordinators(); }
    else { showInviteError(result.detail || 'Invite failed. Please try again.'); btn.disabled = false; btn.textContent = 'Send Invite'; }
  } catch (e) { showInviteError(`Error: ${e.message}`); btn.disabled = false; btn.textContent = 'Send Invite'; }
}
function showInviteError(msg) { const el = document.getElementById('invite-error'); el.textContent = msg; el.style.display = 'block'; }

function openRemoveCoordModal(coordId, coordName) {
  pendingRemoveCoordId = coordId; pendingRemoveCoordName = coordName;
  document.getElementById('remove-coord-modal-msg').textContent =
    `Are you sure you want to remove ${coordName || 'this coordinator'}? They will lose access immediately.`;
  document.getElementById('remove-coord-modal').classList.add('visible');
}
function closeRemoveCoordModal() {
  pendingRemoveCoordId = null; pendingRemoveCoordName = null;
  document.getElementById('remove-coord-modal').classList.remove('visible');
}
async function confirmRemoveCoord() {
  if (!pendingRemoveCoordId || !currentToken) return;
  const coordId = pendingRemoveCoordId; closeRemoveCoordModal();
  try {
    const resp = await fetch(`${DAZZLING_URL}/coordinators/${coordId}`, {
      method: 'DELETE', headers: { 'Authorization': `Bearer ${currentToken}` },
    });
    if (resp.ok) { showToast('Coordinator removed', 'success'); await loadCoordinators(); }
    else { const err = await resp.json().catch(() => ({})); showToast(`Failed: ${err.detail || 'Unknown error'}`, 'error'); }
  } catch (e) { showToast(`Error: ${e.message}`, 'error'); }
}

// ── Load institutions ──────────────────────────────────────────────────────
async function loadInstitutions() {
  if (!currentToken) return;
  if (!isSuperAdmin && !currentInstitutionId) return;
  const statusFilter = document.getElementById('filter-inst-status').value;
  const filterQuery  = statusFilter ? `status=${statusFilter}` : '';
  const instQuery    = !isSuperAdmin && currentInstitutionId ? `institution_id=${currentInstitutionId}` : '';
  const sep          = filterQuery && instQuery ? '&' : '';
  const query        = filterQuery || instQuery ? `?${filterQuery}${sep}${instQuery}` : '';
  document.getElementById('institutions-table-wrap').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading institutions...</div>';
  try {
    const resp = await fetch(`${DAZZLING_URL}/admin/institutions${query}`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    const data = resp.ok ? await resp.json() : { institutions: [] };
    const institutions = data.institutions || [];
    if (!institutions.length) {
      document.getElementById('institutions-table-wrap').innerHTML = '<div class="loading">No institutions found.</div>';
      return;
    }
    const rows = institutions.map(inst => {
      const statusBadge =
        inst.status === 'active'    ? '<span class="badge badge-active">Active</span>' :
        inst.status === 'pending'   ? '<span class="badge badge-pending">Pending</span>' :
        inst.status === 'suspended' ? '<span class="badge badge-suspended">Suspended</span>' : '—';
      let actions = '';
      if (isSuperAdmin) {
        if (inst.status === 'pending') actions = `<button class="btn-approve" onclick="updateInstStatus('${inst.id}', 'active')">Approve</button><button class="btn-suspend" onclick="updateInstStatus('${inst.id}', 'suspended')">Suspend</button>`;
        else if (inst.status === 'active') actions = `<button class="btn-suspend" onclick="updateInstStatus('${inst.id}', 'suspended')">Suspend</button>`;
        else if (inst.status === 'suspended') actions = `<button class="btn-reactivate" onclick="updateInstStatus('${inst.id}', 'active')">Reactivate</button>`;
      }
      return `<tr>
        <td><strong>${escapeHtml(inst.id)}</strong></td>
        <td>${escapeHtml(inst.name || '—')}</td>
        <td style="color:var(--muted)">${escapeHtml(inst.admin_email || '—')}</td>
        <td>${escapeHtml(inst.plan || '—')}</td>
        <td>${statusBadge}</td><td>${actions}</td>
      </tr>`;
    }).join('');
    document.getElementById('institutions-table-wrap').innerHTML = `
      <table>
        <thead><tr><th>ID</th><th>Name</th><th>Admin Email</th><th>Plan</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="table-footer">${institutions.length} institution${institutions.length !== 1 ? 's' : ''}</div>`;
  } catch (e) {
    document.getElementById('institutions-table-wrap').innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${escapeHtml(e.message)}</div>`;
  }
}

async function updateInstStatus(institutionId, newStatus) {
  if (!currentToken || !isSuperAdmin) return;
  const actionLabel = newStatus === 'active' ? 'Approving' : newStatus === 'suspended' ? 'Suspending' : 'Updating';
  showToast(`${actionLabel} ${institutionId}...`, 'success');
  try {
    const formData = new FormData();
    formData.append('status', newStatus);
    const resp = await fetch(`${DAZZLING_URL}/admin/institutions/${institutionId}/status`, {
      method: 'PATCH', headers: { 'Authorization': `Bearer ${currentToken}` }, body: formData,
    });
    if (resp.ok) {
      const label = newStatus === 'active' ? 'approved' : newStatus === 'suspended' ? 'suspended' : 'updated';
      showToast(`✓ ${institutionId} ${label}`, 'success');
      await loadInstitutions(); await fetchPendingCount();
    } else {
      const err = await resp.json(); showToast(`Failed: ${err.detail || 'Unknown error'}`, 'error');
    }
  } catch (e) { showToast(`Error: ${e.message}`, 'error'); }
}

function openDeleteModal(studentId, studentName) {
  pendingDeleteId = studentId; pendingDeleteName = studentName;
  document.getElementById('delete-modal-msg').textContent =
    `Are you sure you want to delete ${studentName}? This will remove all their photos and attendance records permanently.`;
  document.getElementById('delete-modal').classList.add('visible');
}
function closeDeleteModal() {
  pendingDeleteId = null; pendingDeleteName = null;
  document.getElementById('delete-modal').classList.remove('visible');
}
async function confirmDelete() {
  if (!pendingDeleteId || !currentToken) return;
  const studentId = pendingDeleteId; closeDeleteModal();
  try {
    const resp = await fetch(`${DAZZLING_URL}/students/${studentId}`, {
      method: 'DELETE', headers: { 'Authorization': `Bearer ${currentToken}` },
    });
    if (resp.ok) { showToast('Student deleted', 'success'); await loadStudents(); await loadData(); }
    else { const err = await resp.json(); showToast(`Failed: ${err.detail || 'Unknown error'}`, 'error'); }
  } catch (e) { showToast(`Error: ${e.message}`, 'error'); }
}

function applyFilters() {
  const inst   = document.getElementById('filter-inst').value;
  const status = document.getElementById('filter-status').value;
  let filtered = allRecords;
  if (inst)   filtered = filtered.filter(r => r.institution_id === inst);
  if (status) filtered = filtered.filter(r => r.verified === status);
  renderTable(filtered);
}

function renderTable(records) {
  if (!records.length) {
    document.getElementById('table-wrap').innerHTML = '<div class="loading">No records found.</div>';
    return;
  }
  const rows = records.map(r => {
    const ts   = r.timestamp ? new Date(r.timestamp).toLocaleString('en-GB', { timeZone: 'Africa/Nairobi' }) : '—';
    const conf = r.confidence ? (r.confidence * 100).toFixed(1) + '%' : '—';
    const badge = r.verified === 'success' ? '<span class="badge badge-success">Success</span>' :
      r.verified === 'spoof' ? '<span class="badge badge-spoof">Spoof</span>' : '<span class="badge badge-failed">Failed</span>';
    const unitCell = r.course_unit_name
      ? `<span style="color:var(--blue);font-size:0.78rem;">${r.course_unit_name}</span>`
      : `<span style="color:var(--muted);font-size:0.78rem;">—</span>`;
    return `<tr><td>${r.student_id || '—'}</td><td>${badge}</td><td>${conf}</td><td>${unitCell}</td><td>${r.institution_id || '—'}</td><td style="color:var(--muted)">${ts}</td></tr>`;
  }).join('');
  document.getElementById('table-wrap').innerHTML = `
    <table>
      <thead><tr><th>Student ID</th><th>Status</th><th>Confidence</th><th>Course Unit</th><th>Institution</th><th>Time (EAT)</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="table-footer">${records.length} records</div>`;
}

function exportCSV() {
  const inst   = document.getElementById('filter-inst').value;
  const status = document.getElementById('filter-status').value;
  let filtered = allRecords;
  if (inst)   filtered = filtered.filter(r => r.institution_id === inst);
  if (status) filtered = filtered.filter(r => r.verified === status);
  const header = ['student_id', 'verified', 'confidence', 'institution_id', 'course_unit_name', 'timestamp_EAT'];
  const rows = filtered.map(r => [
    r.student_id ?? '',
    r.verified ?? '',
    r.confidence ?? '',
    r.institution_id ?? '',
    r.course_unit_name ?? 'N/A',
    r.timestamp ? new Date(r.timestamp).toLocaleString('en-GB', { timeZone: 'Africa/Nairobi' }) : ''
  ].join(','));
  const csv    = [header.join(','), ...rows].join('\n');
  const blob   = new Blob([csv], { type: 'text/csv' });
  const url    = URL.createObjectURL(blob);
  const a      = document.createElement('a');
  a.href = url; a.download = `attendance_${new Date().toISOString().slice(0,10)}.csv`; a.click();
  URL.revokeObjectURL(url);
}

// ── Idle timeout (5 mins) ──────────────────────────────────────────────────
const IDLE_TIMEOUT_MS = 5 * 60 * 1000;
let idleTimer = null;

function resetIdleTimer() {
  clearTimeout(idleTimer);
  if (!currentToken) return;
  localStorage.setItem('lastActivity', Date.now());
  idleTimer = setTimeout(async () => {
    if (currentToken) {
      showToast('Session expired due to inactivity. Signing out...', 'error');
      await new Promise(r => setTimeout(r, 2000));
      await logout();
    }
  }, IDLE_TIMEOUT_MS);
}

['mousemove', 'keydown', 'click', 'scroll', 'touchstart'].forEach(event => {
  document.addEventListener(event, resetIdleTimer, { passive: true });
});

const _origInitDashboard = initDashboard;
initDashboard = async function(session, isFreshLogin = false) {
  if (!isFreshLogin) {
    const lastActivityRaw = localStorage.getItem('lastActivity');
    const lastActivity = lastActivityRaw ? parseInt(lastActivityRaw, 10) : null;
    if (lastActivity && Date.now() - lastActivity > IDLE_TIMEOUT_MS) {
      showToast('Session expired due to inactivity. Signing out...', 'error');
      await new Promise(r => setTimeout(r, 2000));
      await logout();
      return;
    }
  }
  await _origInitDashboard(session, isFreshLogin);
  resetIdleTimer();
};

// ── Enter key on login ─────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && document.getElementById('login-screen').style.display !== 'none') {
    login();
  }
});
