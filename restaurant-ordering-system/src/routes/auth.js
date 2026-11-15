'use strict';
const express = require('express');
const bcrypt = require('bcryptjs');
const rateLimit = require('express-rate-limit');
const { issueSession, clearSession, requireRole } = require('../auth');
const { HttpError, str } = require('../util');

// Used to keep login timing constant when the username does not exist.
const DUMMY_HASH = bcrypt.hashSync('not-a-real-password', 12);

function validatePassword(pw) {
  const p = str(pw, { field: 'New password', required: true, min: 8, max: 128 });
  if (!/[A-Za-z]/.test(p) || !/[0-9]/.test(p)) throw new HttpError(400, 'New password must contain letters and numbers');
  return p;
}

module.exports = function authRoutes(db, { loginLimit = 10 } = {}) {
  const r = express.Router();
  const byName = db.prepare('SELECT * FROM users WHERE username = ?');
  const byId = db.prepare('SELECT * FROM users WHERE id = ?');
  const setPw = db.prepare('UPDATE users SET password_hash = ? WHERE id = ?');

  const limiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    limit: loginLimit,
    skipSuccessfulRequests: true,
    standardHeaders: 'draft-7',
    legacyHeaders: false,
    message: { error: 'Too many failed sign-in attempts. Try again in 15 minutes.' },
  });

  r.post('/login', limiter, async (req, res) => {
    const username = str(req.body && req.body.username, { field: 'Username', required: true, max: 50 });
    const password = str(req.body && req.body.password, { field: 'Password', required: true, max: 128 });
    const user = byName.get(username);
    const ok = await bcrypt.compare(password, user ? user.password_hash : DUMMY_HASH);
    if (!user || !ok) throw new HttpError(401, 'Incorrect username or password');
    issueSession(res, user);
    res.json({ id: user.id, username: user.username, role: user.role });
  });

  r.post('/logout', (_req, res) => {
    clearSession(res);
    res.json({ ok: true });
  });

  r.get('/me', requireRole(), (req, res) => res.json(req.user));

  r.post('/change-password', requireRole(), async (req, res) => {
    const current = str(req.body && req.body.current_password, { field: 'Current password', required: true, max: 128 });
    const next = validatePassword(req.body && req.body.new_password);
    const user = byId.get(req.user.id);
    if (!(await bcrypt.compare(current, user.password_hash))) throw new HttpError(400, 'Current password is incorrect');
    setPw.run(await bcrypt.hash(next, 12), user.id);
    res.json({ ok: true });
  });

  return r;
};

module.exports.validatePassword = validatePassword;
