'use strict';
const crypto = require('crypto');
const { getSettings } = require('../db');
const { bad, str, int, moneyToCents } = require('../util');

const ORDER_TYPES = ['dine_in', 'takeaway', 'delivery'];
const STATUSES = ['pending', 'preparing', 'ready', 'completed', 'cancelled'];
const PHONE_RE = /^\+?[0-9][0-9 ()-]{6,19}$/;

/** SQLite stores UTC "YYYY-MM-DD HH:MM:SS"; expose ISO-8601 so browsers convert to local time. */
const iso = (s) => (s ? `${s.replace(' ', 'T')}Z` : s);

function serializeOrder(order, items) {
  return {
    id: order.id,
    order_number: order.order_number,
    public_token: order.public_token,
    customer_name: order.customer_name,
    customer_phone: order.customer_phone,
    order_type: order.order_type,
    table_number: order.table_number,
    delivery_address: order.delivery_address,
    notes: order.notes,
    status: order.status,
    payment_status: order.payment_status,
    subtotal_cents: order.subtotal_cents,
    tax_cents: order.tax_cents,
    delivery_fee_cents: order.delivery_fee_cents,
    total_cents: order.total_cents,
    created_at: iso(order.created_at),
    updated_at: iso(order.updated_at),
    items: items.map((i) => ({
      id: i.id,
      dish_id: i.dish_id,
      dish_name: i.dish_name,
      unit_price_cents: i.unit_price_cents,
      quantity: i.quantity,
      line_total_cents: i.line_total_cents,
    })),
  };
}

function makeOrderService(db) {
  const q = {
    dish: db.prepare('SELECT id, name, price_cents, is_available FROM dishes WHERE id = ?'),
    table: db.prepare('SELECT * FROM restaurant_tables WHERE table_number = ?'),
    insertOrder: db.prepare(`INSERT INTO orders
      (order_number, public_token, customer_name, customer_phone, order_type, table_number,
       delivery_address, notes, subtotal_cents, tax_cents, delivery_fee_cents, total_cents)
      VALUES (@order_number, @public_token, @customer_name, @customer_phone, @order_type, @table_number,
       @delivery_address, @notes, @subtotal_cents, @tax_cents, @delivery_fee_cents, @total_cents)`),
    setNumber: db.prepare('UPDATE orders SET order_number = ? WHERE id = ?'),
    insertItem: db.prepare(`INSERT INTO order_items
      (order_id, dish_id, dish_name, unit_price_cents, quantity, line_total_cents)
      VALUES (?, ?, ?, ?, ?, ?)`),
    byId: db.prepare('SELECT * FROM orders WHERE id = ?'),
    byToken: db.prepare('SELECT * FROM orders WHERE public_token = ?'),
    items: db.prepare('SELECT * FROM order_items WHERE order_id = ? ORDER BY id'),
  };

  function load(order) {
    return order ? serializeOrder(order, q.items.all(order.id)) : null;
  }

  function validate(body) {
    if (!body || typeof body !== 'object') throw bad('Invalid request');
    const customer_name = str(body.customer_name, { field: 'Name', required: true, min: 2, max: 60 });
    const order_type = String(body.order_type || '');
    if (!ORDER_TYPES.includes(order_type)) throw bad('Please choose Dine-in, Takeaway or Delivery');

    const customer_phone = str(body.customer_phone, { field: 'Phone number', max: 20 });
    if (customer_phone && !PHONE_RE.test(customer_phone)) throw bad('Please enter a valid phone number');
    const notes = str(body.notes, { field: 'Notes', max: 300 });

    let table_number = null;
    let delivery_address = '';
    if (order_type === 'dine_in') {
      table_number = int(body.table_number, { field: 'Table number', min: 1, max: 9999 });
      const table = q.table.get(table_number);
      if (!table || !table.is_active) throw bad(`Table ${table_number} does not exist. Please check the number on your table.`);
    } else if (order_type === 'delivery') {
      if (!customer_phone) throw bad('Phone number is required for delivery');
      delivery_address = str(body.delivery_address, { field: 'Delivery address', required: true, min: 10, max: 300 });
    }

    if (!Array.isArray(body.items) || body.items.length === 0) throw bad('Your cart is empty');
    if (body.items.length > 50) throw bad('Too many different items in one order');
    const merged = new Map();
    for (const it of body.items) {
      const dishId = int(it && it.dish_id, { field: 'Dish', min: 1 });
      const qty = int(it && it.quantity, { field: 'Quantity', min: 1, max: 50 });
      merged.set(dishId, (merged.get(dishId) || 0) + qty);
    }

    const lines = [];
    for (const [dishId, qty] of merged) {
      if (qty > 50) throw bad('Maximum quantity per dish is 50');
      const dish = q.dish.get(dishId);
      if (!dish) throw bad('One of the dishes in your cart is no longer on the menu');
      if (!dish.is_available) throw bad(`Sorry, ${dish.name} is currently unavailable`);
      lines.push({ dish, qty, line: dish.price_cents * qty });
    }
    return { customer_name, customer_phone, order_type, table_number, delivery_address, notes, lines };
  }

  const createTx = db.transaction((input) => {
    const s = getSettings(db);
    const taxRate = Number(s.tax_rate_percent) || 0;
    const subtotal = input.lines.reduce((a, l) => a + l.line, 0);
    const tax = Math.round((subtotal * taxRate) / 100);
    const deliveryFee = input.order_type === 'delivery' ? moneyToCents(s.delivery_fee || 0, 'Delivery fee') : 0;
    const token = crypto.randomBytes(16).toString('hex');
    const info = q.insertOrder.run({
      order_number: `tmp-${token}`,
      public_token: token,
      customer_name: input.customer_name,
      customer_phone: input.customer_phone,
      order_type: input.order_type,
      table_number: input.table_number,
      delivery_address: input.delivery_address,
      notes: input.notes,
      subtotal_cents: subtotal,
      tax_cents: tax,
      delivery_fee_cents: deliveryFee,
      total_cents: subtotal + tax + deliveryFee,
    });
    const id = Number(info.lastInsertRowid);
    q.setNumber.run(String(1000 + id), id);
    for (const l of input.lines) q.insertItem.run(id, l.dish.id, l.dish.name, l.dish.price_cents, l.qty, l.line);
    return id;
  });

  return {
    create(body) {
      const input = validate(body);
      return load(q.byId.get(createTx(input)));
    },
    getById: (id) => load(q.byId.get(id)),
    getByToken: (token) => (typeof token === 'string' && /^[a-f0-9]{32}$/.test(token) ? load(q.byToken.get(token)) : null),
    load,
  };
}

module.exports = { makeOrderService, serializeOrder, ORDER_TYPES, STATUSES, iso };
