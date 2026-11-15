'use strict';
const path = require('path');
const express = require('express');
const helmet = require('helmet');
const cookieParser = require('cookie-parser');
const config = require('./config');
const { openDatabase } = require('./db');
const { loadUser, sameOrigin } = require('./auth');
const { HttpError } = require('./util');
const { makeOrderService } = require('./services/orders');

function createApp({ dbFile = config.dbFile, loginLimit, orderLimit } = {}) {
  const db = openDatabase(dbFile);
  const orders = makeOrderService(db);
  const app = express();

  app.disable('x-powered-by');
  if (config.trustProxy) app.set('trust proxy', 1);

  app.use(helmet({
    contentSecurityPolicy: {
      useDefaults: true,
      directives: {
        'default-src': ["'self'"],
        'script-src': ["'self'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", 'data:', 'blob:', 'https:'],
        'connect-src': ["'self'"],
        'frame-src': ["'self'"],
        'object-src': ["'none'"],
        'upgrade-insecure-requests': config.cookieSecure ? [] : null,
      },
    },
    crossOriginEmbedderPolicy: false,
    // Allow the browser's built-in PDF viewer to show bills inside an <iframe> on our own pages.
    frameguard: { action: 'sameorigin' },
  }));
  app.use(express.json({ limit: '100kb' }));
  app.use(cookieParser());
  app.use(loadUser(db));
  app.use('/api', sameOrigin);

  app.get('/api/health', (_req, res) => res.json({ ok: true }));
  app.use('/api/auth', require('./routes/auth')(db, { loginLimit }));
  app.use('/api/orders', require('./routes/orders')(db, orders)); // staff list/status/bill (must precede public POST)
  app.use('/api', require('./routes/public')(db, orders, { orderLimit }));
  app.use('/api/admin', require('./routes/admin')(db));
  app.use('/api', (_req, _res, next) => next(new HttpError(404, 'Not found')));

  app.use('/uploads', express.static(config.uploadsDir, { maxAge: '7d', fallthrough: false }));
  app.use(express.static(path.join(config.root, 'public'), { extensions: ['html'], maxAge: '1h' }));

  // Error handler: JSON for API, plain text otherwise. Never leak stack traces.
  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, _next) => {
    let status = err.status || err.statusCode || 500;
    if (err.type === 'entity.parse.failed') status = 400;
    const message = status >= 500 ? 'Something went wrong. Please try again.' : err.message || 'Request failed';
    if (status >= 500) console.error(err);
    if (res.headersSent) return res.end();
    if (req.path.startsWith('/api') || req.path.startsWith('/uploads')) res.status(status).json({ error: status === 400 && err.type === 'entity.parse.failed' ? 'Invalid JSON' : message });
    else res.status(status).type('text').send(message);
  });

  app.locals.db = db;
  return app;
}

module.exports = { createApp };
