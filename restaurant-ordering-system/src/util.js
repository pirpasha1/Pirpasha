'use strict';

class HttpError extends Error {
  constructor(status, message, details) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

const bad = (msg, details) => new HttpError(400, msg, details);

function str(value, { field, min = 0, max = 255, required = false } = {}) {
  if (value === undefined || value === null) value = '';
  if (typeof value !== 'string' && typeof value !== 'number') throw bad(`${field} must be text`);
  const v = String(value).trim();
  if (required && v.length === 0) throw bad(`${field} is required`);
  if (v.length < min) throw bad(`${field} must be at least ${min} characters`);
  if (v.length > max) throw bad(`${field} must be at most ${max} characters`);
  return v;
}

function int(value, { field, min = -Infinity, max = Infinity, required = true } = {}) {
  if ((value === undefined || value === null || value === '') && !required) return null;
  const n = Number(value);
  if (!Number.isInteger(n)) throw bad(`${field} must be a whole number`);
  if (n < min || n > max) throw bad(`${field} must be between ${min} and ${max}`);
  return n;
}

/** Parse a money amount like "249.50" into integer cents. */
function moneyToCents(value, field = 'Price') {
  const n = Number(value);
  if (value === '' || value === null || value === undefined || !Number.isFinite(n)) throw bad(`${field} must be a number`);
  if (n < 0 || n > 1000000) throw bad(`${field} must be between 0 and 1,000,000`);
  return Math.round(n * 100);
}

function bool(value) {
  return value === true || value === 1 || value === '1' || value === 'true' || value === 'on';
}

function formatMoney(cents, symbol = '₹') {
  const v = (cents / 100).toFixed(2);
  const [whole, frac] = v.split('.');
  return `${symbol}${Number(whole).toLocaleString('en-IN')}.${frac}`;
}

const asyncH = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

module.exports = { HttpError, bad, str, int, moneyToCents, bool, formatMoney, asyncH };
