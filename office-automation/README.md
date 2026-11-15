# Office Automation – Excel & PDF System

A web app for office work that runs on **Android phones**, **desktop computers** and in any modern **browser**. It can be **installed like a normal app** (Progressive Web App, PWA).

**Current phase: Foundation ✅**

| Done | Feature |
| --- | --- |
| ✅ | Professional dashboard with simple navigation |
| ✅ | Works on phones (slide-out menu) and desktops (side menu) |
| ✅ | Installable app (PWA), opens quickly, works with weak internet |
| ✅ | Sign in, sign out, create account, forgot password |
| ✅ | Two roles: **Administrator** and **Staff** |
| ✅ | Database security (Row Level Security) |
| ✅ | Activity log (who signed in/out, role changes, …) |
| ✅ | User management for administrators (change roles) |
| ⏳ | Excel Tools (ExcelJS) – next phase |
| ⏳ | PDF Tools (pdf-lib) – next phase |

---

## 1. What you need

1. **Node.js 20 or newer**: download the "LTS" version from <https://nodejs.org> and install it.
2. A free **Supabase** account: <https://supabase.com>.
3. A code editor. **VS Code** is recommended: <https://code.visualstudio.com>.

To check Node.js is installed, open a terminal (Windows: "Command Prompt", Mac: "Terminal") and type:

```bash
node -v
```

You should see a version number such as `v22.x.x`.

---

## 2. Set up Supabase (one time only)

Supabase is the online service that stores the user accounts and data.

1. Sign in at <https://supabase.com> and click **New project**. Choose a name, a strong database password (save it somewhere safe) and the region closest to you. Wait about 2 minutes while it is created.
2. **Create the database tables and security rules:**
   - In the left menu open **SQL Editor** → **New query**.
   - Open the file `supabase/migrations/0001_foundation.sql` from this project, copy **all** of it, and paste it into the editor.
   - Click **Run**. You should see "Success. No rows returned". (Running it again later is safe.)
3. **Allow the password-reset link to return to your app:**
   - Open **Authentication → URL Configuration**.
   - **Site URL**: `http://localhost:5173` (change this to your real web address later).
   - Under **Redirect URLs**, add `http://localhost:5173/**`.
4. **Copy your connection details:** open **Project Settings → API** (called "Data API" / "API Keys" in some versions). You need:
   - the **Project URL**, which looks like `https://abcdefgh.supabase.co`;
   - the **anon** (or **publishable**) key, a long text.

   ⚠️ Never use the **service_role / secret** key in this app. It bypasses all security.

---

## 3. Run the app on your computer

Open a terminal **inside the `office-automation` folder** and run:

```bash
npm install
```

This downloads the libraries the app needs (takes 1–2 minutes the first time).

Next, create your settings file:

- Copy the file `.env.example` and name the copy `.env`.
- Open `.env` and paste your **Project URL** and **anon key** from step 2.4:

```env
VITE_SUPABASE_URL=https://abcdefgh.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOi...your-key...
VITE_ALLOW_SIGNUP=true
```

Start the app:

```bash
npm run dev
```

Open <http://localhost:5173> in your browser.

> If you see **"Setup required"**, the `.env` file is missing or incomplete. Fix it, then stop the app (press `Ctrl + C` in the terminal) and run `npm run dev` again.

### Create the first administrator

1. On the sign-in screen click **Create an account**, then enter your name, email and a password (at least 8 characters).
2. If Supabase sends you a confirmation email, click the link in it, then sign in.
3. **The very first account automatically becomes the Administrator.** Everyone who signs up after that is **Staff**.

> **Tip for testing:** to skip confirmation emails while testing, turn off *Authentication → Sign In / Providers → Email → Confirm email* in Supabase. Turn it back on before real use.

### Test on your Android phone (same Wi-Fi)

```bash
npm run dev -- --host
```

The terminal shows a "Network" address such as `http://192.168.1.20:5173`. Open it in Chrome on your phone.
(Installing as an app needs **HTTPS**, which you get after publishing; see section 7.)

---

## 4. Roles: who can do what

| | Staff | Administrator |
| --- | :---: | :---: |
| Dashboard, Excel Tools, PDF Tools, Settings | ✅ | ✅ |
| See **own** activity history | ✅ | ✅ |
| See **everyone's** activity history | ❌ | ✅ |
| User Management (see all users, change roles) | ❌ | ✅ |
| Make yourself an administrator | ❌ | – |
| Remove the last administrator | ❌ | ❌ (blocked so you can't lock yourself out) |

**Adding staff:** people can create their own account from the sign-in screen and start as Staff. To stop public sign-ups, set `VITE_ALLOW_SIGNUP=false` in `.env` **and** turn off *Allow new users to sign up* in Supabase (*Authentication → Sign In / Providers*). You can then add users yourself in Supabase under **Authentication → Users → Add user**.

**Making someone an admin:** open **User Management** in the app and change their role. (Emergency option: in the Supabase SQL Editor run
`update public.profiles set role = 'admin' where email = 'person@example.com';`)

---

## 5. How the security works (simple explanation)

- Hiding a menu item is **not** security; anyone could type the address. The real protection is inside the database.
- **Row Level Security (RLS)** is switched on for every table. For every request, the database itself checks who is asking:
  - visitors who are not signed in can read **nothing**;
  - staff can read and edit **only their own** profile and see only their own activity;
  - only administrators can see all users and change roles, and the database refuses role changes from anyone else, even if they tamper with the app;
  - the activity log can be added to but **never edited or deleted** from the app.
- The key in `.env` is the public "anon" key, made to be used in browsers. It is safe because of the rules above.
- `.env` is listed in `.gitignore`, so it is never uploaded to GitHub.

---

## 6. Project structure

```
office-automation/
├── public/                   App icons and logo (used when installing the app)
├── scripts/generate-icons.mjs  Recreates the PNG icons from public/favicon.svg
├── src/
│   ├── main.tsx              Starts the app and registers the PWA service worker
│   ├── App.tsx               List of all pages and who may open them
│   ├── index.css             All styles (colors at the top, phone layout at the bottom)
│   ├── config/modules.ts     The navigation menu – add new modules here
│   ├── context/              Login state (useAuth) shared by all screens
│   ├── components/           Reusable pieces: layout, menus, cards, route guard
│   ├── lib/                  Supabase connection, activity log, helpers, types
│   └── pages/                One file per screen
├── supabase/migrations/      Database tables + security rules (SQL)
├── tests/
│   ├── db/                   Database security tests (real PostgreSQL in memory)
│   └── e2e/                  Browser tests (clicks through the real app)
├── .env.example              Template for your settings
└── vite.config.ts            Build + PWA (install) configuration
```

---

## 7. Useful commands

| Command | What it does |
| --- | --- |
| `npm run dev` | Start the app for development at <http://localhost:5173> |
| `npm run build` | Create the final, optimized app in the `dist/` folder |
| `npm run preview` | Preview the built app locally |
| `npm test` | Run **all** checks: type check, lint, database security tests and browser tests |
| `npm run test:db` | Only the database security tests |
| `npm run test:e2e` | Only the browser tests (needs Chromium: `npx playwright install chromium`) |
| `npm run icons` | Regenerate the app icons after changing `public/favicon.svg` |

### Publishing (making it available online)

Any static web host works (Netlify, Vercel, Cloudflare Pages, …):

- **Build command:** `npm run build`, **output folder:** `dist`
- Add the same `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` values as environment variables in the host's settings.
- Configure "single-page app" routing so every address serves `index.html` (for Netlify and Cloudflare Pages this is already done by the included `public/_redirects` file; Vercel does it automatically for Vite).
- Update **Site URL** and **Redirect URLs** in Supabase to your new web address.
- Once it's online with **HTTPS**, Android Chrome and desktop Chrome/Edge will offer **Install app**.

---

## 8. Notes

- `npm audit` reports moderate warnings in **build-time** tools used by the PWA plugin (`workbox-build`). They do not end up in the app that users download. They will be resolved when the plugin publishes an update.
- **ExcelJS** and **pdf-lib** are already installed for the next phase. They are loaded only when the Excel/PDF tools are built, so the app stays fast.

## Next phase (planned)

1. Excel Tools: open/preview `.xlsx`, templates, merge files, data cleanup, export to PDF.
2. PDF Tools: merge, split, rotate/reorder pages, page numbers and watermark, generate documents from templates.
3. Reports built from the processed files.
