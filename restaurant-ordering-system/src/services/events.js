'use strict';
const { EventEmitter } = require('events');

/** In-process bus that fans order events out to Server-Sent-Event clients. */
const bus = new EventEmitter();
bus.setMaxListeners(200);

function sseHandler(req, res) {
  res.set({
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache, no-transform',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });
  res.flushHeaders();
  res.write('retry: 3000\n\n');

  const send = (event, data) => res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  const onCreated = (o) => send('order_created', o);
  const onUpdated = (o) => send('order_updated', o);
  bus.on('order_created', onCreated);
  bus.on('order_updated', onUpdated);
  const ping = setInterval(() => res.write(': ping\n\n'), 25000);

  req.on('close', () => {
    clearInterval(ping);
    bus.off('order_created', onCreated);
    bus.off('order_updated', onUpdated);
  });
}

module.exports = { bus, sseHandler };
