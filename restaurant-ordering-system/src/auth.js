'use strict';
const jwt = require('jsonwebtoken');
const config = require('./config');
const { HttpError } = require('./util');

const COOKIE = 'rsid';
const MAX_AGE_MS = 8 * 60 * 60 * 1000;

function issueSession(res, user) {
  const token = jwt.sign({ sub: user.id, role: user.role, username: user.username }, config.jwtSecret, {
    expiresIn: Math.floor(MAX_AGE_MS / 1000),
    algorithm: 'HS256',
  });
  res.cookie(COOKIE, token, {
    httpOnly: true,
    sameSite: 'strict',
    secure: config.cookieSecure,
    maxAge: MAX_AGE_MS,
    path: '/',
  });
}

function clearSession(res) {
  res.clearCookie(COOKIE, { httpOnly: true, sameSite: 'strict', secure: config.cookieSecure, path: '/' });
}

/** Attaches req.user when a valid session cookie is present (user must still exist). */
function loadUser(db) {
  const findUser = db.prepare('SELECT id, username, role FROM users WHERE id = ?');
  return (req, _res, next) => {
    const token = req.cookies && req.cookies[COOKIE];
    if (token) {
      try {
        const payload = jwt.verify(token, config.jwtSecret, { algorithms: ['HS256'] });
        const user = findUser.get(payload.sub);
        if (user) req.user = user;
      } catch (_) { /* invalid / expired token → anonymous */ }
    }
    next();
  };
}

function requireRole(...roles) {
  return (req, _res, next) => {
    if (!req.user) return next(new HttpError(401, 'Please sign in'));
    if (roles.length && !roles.includes(req.user.role)) return next(new HttpError(403, 'You do not have access to this'));
    next();
  };
}

/**
 * Defence-in-depth against CSRF: state-changing requests that carry a session
 * must come from our own origin (SameSite=Strict already blocks most cases).
 */
function sameOrigin(req, _res, next) {
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) return next();
  const origin = req.get('origin');
  if (!origin) return next();
  try {
    const host = req.get('host');
    if (new URL(origin).host !== host) return next(new HttpError(403, 'Cross-origin request blocked'));
  } catch (_) {
    return next(new HttpError(403, 'Cross-origin request blocked'));
  }
  next();
}

module.exports = { issueSession, clearSession, loadUser, requireRole, sameOrigin, COOKIE };
