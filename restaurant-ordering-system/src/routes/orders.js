'use strict';
const express = require('express');
const { getSettings } = require('../db');
const { requireRole } = require('../auth');
const { HttpError, int, str } = require('../util');
const { STATUSES } = require('../services/orders');
const { bus, sseHandler } = require('../services/events');
const { sendBill } = require('./public');

// Allowed status transitions. Completed and cancelled are final.
const TRANSITIONS = {
  pending: ['preparing', 'ready', 'cancelled'],
  preparing: ['ready', 'pending', 'cancelled'],
  ready: ['completed', 'preparing', 'cancelled'],
  completed: [],
  cancelled: [],
};

const ACTIVE = ['pending', 'preparing', 'ready'];

module.exports = function orderRoutes(db, orders) {
  const r = express.Router();
  const staff = requireRole('admin', 'kitchen');
  const admin = requireRole('admin');

  const setStatus = db.prepare("UPDATE orders SET status = ?, updated_at = datetime('now') WHERE id = ?");
  const setPayment = db.prepare("UPDATE orders SET payment_status = ?, updated_at = datetime('now') WHERE id = ?");
  const getRaw = db.prepare('SELECT * FROM orders WHERE id = ?');

  r.get('/stream', staff, sseHandler);

  r.get('/', staff, (req, res) => {
    const where = [];
    const params = {};
    const status = String(req.query.status || 'active');
    if (status === 'active') where.push(`status IN (${ACTIVE.map((s) => `'${s}'`).join(',')})`);
    else if (STATUSES.includes(status)) { where.push('status = @status'); params.status = status; }
    else if (status !== 'all') throw new HttpError(400, 'Unknown status filter');

    // from/to are UTC instants (ISO strings) computed by the browser for the local day.
    for (const [k, op] of [['from', '>='], ['to', '<']]) {
      if (req.query[k]) {
        const d = new Date(String(req.query[k]));
        if (Number.isNaN(d.getTime())) throw new HttpError(400, `Invalid ${k} date`);
        params[k] = d.toISOString().replace('T', ' ').slice(0, 19);
        where.push(`created_at ${op} @${k}`);
      }
    }
    const search = str(req.query.q, { field: 'Search', max: 60 });
    if (search) {
      params.q = `%${search.replace(/[%_\\]/g, (m) => `\\${m}`)}%`;
      where.push("(customer_name LIKE @q ESCAPE '\\' OR order_number LIKE @q ESCAPE '\\' OR customer_phone LIKE @q ESCAPE '\\')");
    }
    const limit = int(req.query.limit || 200, { field: 'Limit', min: 1, max: 500 });
    const sql = `SELECT * FROM orders ${where.length ? `WHERE ${where.join(' AND ')}` : ''}
      ORDER BY ${status === 'active' ? 'created_at ASC' : 'created_at DESC'}, id DESC LIMIT ${limit}`;
    res.set('Cache-Control', 'no-store').json(db.prepare(sql).all(params).map(orders.load));
  });

  r.get('/:id', staff, (req, res) => {
    const order = orders.getById(int(req.params.id, { field: 'Order id', min: 1 }));
    if (!order) throw new HttpError(404, 'Order not found');
    res.json(order);
  });

  r.patch('/:id/status', staff, (req, res) => {
    const id = int(req.params.id, { field: 'Order id', min: 1 });
    const next = String((req.body && req.body.status) || '');
    if (!STATUSES.includes(next)) throw new HttpError(400, 'Unknown status');
    const current = getRaw.get(id);
    if (!current) throw new HttpError(404, 'Order not found');
    if (current.status !== next && !TRANSITIONS[current.status].includes(next)) {
      throw new HttpError(409, `Cannot change an order from "${current.status}" to "${next}"`);
    }
    setStatus.run(next, id);
    const order = orders.getById(id);
    bus.emit('order_updated', order);
    res.json(order);
  });

  r.patch('/:id/payment', admin, (req, res) => {
    const id = int(req.params.id, { field: 'Order id', min: 1 });
    const p = String((req.body && req.body.payment_status) || '');
    if (!['paid', 'unpaid'].includes(p)) throw new HttpError(400, 'Payment status must be paid or unpaid');
    if (!getRaw.get(id)) throw new HttpError(404, 'Order not found');
    setPayment.run(p, id);
    const order = orders.getById(id);
    bus.emit('order_updated', order);
    res.json(order);
  });

  r.get('/:id/bill.pdf', staff, (req, res) => {
    const order = orders.getById(int(req.params.id, { field: 'Order id', min: 1 }));
    if (!order) throw new HttpError(404, 'Order not found');
    sendBill(res, order, getSettings(db), req.query.format, req.query.download);
  });

  return r;
};

