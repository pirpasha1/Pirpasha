'use strict';
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

const root = path.resolve(__dirname, '..');
const dataDir = path.resolve(process.env.DATA_DIR || path.join(root, 'data'));
fs.mkdirSync(dataDir, { recursive: true });

function loadSecret() {
  if (process.env.JWT_SECRET && process.env.JWT_SECRET.length >= 32) return process.env.JWT_SECRET;
  const file = path.join(dataDir, '.jwt-secret');
  if (fs.existsSync(file)) return fs.readFileSync(file, 'utf8').trim();
  const secret = crypto.randomBytes(48).toString('hex');
  fs.writeFileSync(file, secret, { mode: 0o600 });
  return secret;
}

module.exports = {
  root,
  dataDir,
  port: Number(process.env.PORT) || 3000,
  host: process.env.HOST || '0.0.0.0',
  dbFile: process.env.DB_FILE || path.join(dataDir, 'restaurant.db'),
  uploadsDir: path.join(dataDir, 'uploads'),
  jwtSecret: loadSecret(),
  cookieSecure: process.env.COOKIE_SECURE === 'true',
  trustProxy: process.env.TRUST_PROXY === 'true',
  adminUsername: process.env.ADMIN_USERNAME || 'admin',
  adminPassword: process.env.ADMIN_PASSWORD || 'Admin@123',
  kitchenUsername: process.env.KITCHEN_USERNAME || 'kitchen',
  kitchenPassword: process.env.KITCHEN_PASSWORD || 'Kitchen@123',
};
