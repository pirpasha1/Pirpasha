'use strict';
const express = require('express');
const rateLimit = require('express-rate-limit');
const { getSettings } = require('../db');
const { HttpError, int } = require('../util');
const { renderBill } = require('../services/pdf');
const { bus } = require('../services/events');

const PUBLIC_SETTINGS = ['restaurant_name', 'restaurant_address', 'restaurant_phone', 'currency_symbol', 'tax_rate_percent', 'delivery_fee'];

module.exports = function publicRoutes(db, orders, { orderLimit = 30 } = {}) {
  const r = express.Router();

  const listCats = db.prepare('SELECT id, name FROM categories ORDER BY sort_order, name');
  const listDishes = db.prepare(`SELECT id, category_id, name, description, price_cents, image_url, is_veg, is_available
    FROM dishes ORDER BY sort_order, name`);
  const getTable = db.prepare('SELECT table_number, seats, is_active FROM restaurant_tables WHERE table_number = ?');

  r.get('/menu', (_req, res) => {
    const s = getSettings(db);
    const settings = Object.fromEntries(PUBLIC_SETTINGS.map((k) => [k, s[k]]));
    const dishes = listDishes.all().map((d) => ({ ...d, is_veg: !!d.is_veg, is_available: !!d.is_available }));
    const categories = listCats.all().map((c) => ({ ...c, dishes: dishes.filter((d) => d.category_id === c.id) }));
    res.set('Cache-Control', 'no-store').json({ settings, categories });
  });

  r.get('/tables/:number', (req, res) => {
    const n = int(req.params.number, { field: 'Table number', min: 1, max: 9999 });
    const t = getTable.get(n);
    if (!t || !t.is_active) throw new HttpError(404, `Table ${n} not found`);
    res.json({ table_number: t.table_number, seats: t.seats });
  });

  const placeLimiter = rateLimit({
    windowMs: 10 * 60 * 1000,
    limit: orderLimit,
    standardHeaders: 'draft-7',
    legacyHeaders: false,
    message: { error: 'Too many orders from this device. Please wait a few minutes.' },
  });

  r.post('/orders', placeLimiter, (req, res) => {
    const order = orders.create(req.body);
    bus.emit('order_created', order);
    res.status(201).json(order);
  });

  r.get('/public/orders/:token', (req, res) => {
    const order = orders.getByToken(req.params.token);
    if (!order) throw new HttpError(404, 'Order not found');
    res.set('Cache-Control', 'no-store').json(order);
  });

  r.get('/public/orders/:token/bill.pdf', (req, res) => {
    const order = orders.getByToken(req.params.token);
    if (!order) throw new HttpError(404, 'Order not found');
    sendBill(res, order, getSettings(db), req.query.format, req.query.download);
  });

  return r;
};

function sendBill(res, order, settings, format, download) {
  res.set('Content-Type', 'application/pdf');
  res.set('Content-Disposition', `${download ? 'attachment' : 'inline'}; filename="bill-${order.order_number}.pdf"`);
  res.set('Cache-Control', 'no-store');
  renderBill(order, settings, format === 'receipt' ? 'receipt' : 'a4').pipe(res);
}

module.exports.sendBill = sendBill;
