'use strict';
const os = require('os');
const config = require('./src/config');
const { createApp } = require('./src/app');

const app = createApp();
const server = app.listen(config.port, config.host, () => {
  const urls = [`http://localhost:${config.port}`];
  for (const ifaces of Object.values(os.networkInterfaces())) {
    for (const i of ifaces || []) if (i.family === 'IPv4' && !i.internal) urls.push(`http://${i.address}:${config.port}`);
  }
  console.log('\n🍽  Restaurant ordering system is running');
  urls.forEach((u) => console.log(`   ${u}`));
  console.log(`\n   Menu:     /\n   Kitchen:  /kitchen\n   Admin:    /admin\n`);
  if (!process.env.ADMIN_PASSWORD) {
    console.log('   ⚠  Default staff passwords are in use (admin / Admin@123, kitchen / Kitchen@123).');
    console.log('      Sign in and change them under Admin → Staff.\n');
  }
});

function shutdown() {
  server.close(() => {
    app.locals.db.close();
    process.exit(0);
  });
  setTimeout(() => process.exit(0), 3000).unref();
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
