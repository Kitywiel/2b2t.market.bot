# this is the oficial code behind the 2b2t.market bot

## commands

/test

## updates

test

Non at this time

other info

```markdown
# 2b2t.market.bot (Discord bot - Node.js)

This repository contains a minimal Discord bot (Node.js) for quick testing:
- prefix commands: !ping, !echo, !menu, !helpview
- interactive menu with buttons and a modal
- local submissions saved to submissions.csv for testing without Google

Quick start (local)
1. Copy .env.example to .env and set BOT_TOKEN (do NOT commit .env)
2. Install:
   npm install
3. Run:
   npm start
   (or: node index.js)

Replit
1. Create a new Python/Node Repl or import this GitHub repo.
2. Add a Secret named BOT_TOKEN (value = your bot token).
3. Run. Optionally use the web view URL + uptime monitor to reduce sleeping.

Render
- Deploy as a Background Worker.
- Start command: node index.js
- Set BOT_TOKEN in Render Environment.

Notes
- Submissions are stored locally (submissions.csv). For persistence across deploys, integrate with Google Sheets or a database.
- Keep BOT_TOKEN and any service account credentials secret.
- To add Google Sheets later: create a service account, base64 the JSON, set GOOGLE_SERVICE_ACCOUNT_JSON_B64 secret and I can provide the sheets integration code.
```
