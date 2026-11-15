(function () {
  'use strict';
  const { api } = window.App;
  const form = document.getElementById('loginForm');
  const err = document.getElementById('err');
  const btn = document.getElementById('submitBtn');

  function target(role) {
    const next = new URLSearchParams(location.search).get('next') || '';
    // Only allow same-site relative paths to prevent open redirects.
    if (/^\/(?!\/)[\w\-/?=&.%]*$/.test(next) && !next.startsWith('/login')) {
      if (role === 'kitchen' && next.startsWith('/admin')) return '/kitchen';
      return next;
    }
    return role === 'kitchen' ? '/kitchen' : '/admin';
  }

  // Already signed in? Go straight to the dashboard.
  api('/api/auth/me').then((me) => { location.replace(target(me.role)); }).catch(() => {});

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    err.hidden = true;
    const username = form.username.value.trim();
    const password = form.password.value;
    if (!username || !password) {
      err.textContent = 'Enter your username and password';
      err.hidden = false;
      return;
    }
    btn.disabled = true;
    btn.textContent = 'Signing in…';
    try {
      const me = await api('/api/auth/login', { method: 'POST', body: { username, password } });
      location.replace(target(me.role));
    } catch (ex) {
      err.textContent = ex.message;
      err.hidden = false;
      btn.disabled = false;
      btn.textContent = 'Sign in';
      form.password.select();
    }
  });
})();
