# LogiSource Integrated System — Full Export

Exported: 2026-07-23T09:22:46.550278+00:00
By:       febroherdyanto98@gmail.com
Build:    included

## Contents
- `backend/`         — FastAPI Python source + `.env` (rotate secrets before production!)
- `frontend/`        — React app source (run `yarn install` to restore node_modules)
- `frontend/build/`  — Pre-built static bundle ready for static hosting
- `database/`        — MongoDB dump (BSON via mongodump, or JSON fallback if mongodump unavailable)
- `memory/`          — PRD.md, test_credentials.md

## Restore locally

### 1. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Ensure MongoDB is running locally, then:
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### 2. Frontend (dev)
```bash
cd frontend
yarn install
yarn start          # runs on http://localhost:3000
```

### 3. Database restore
If you have BSON dump:
```bash
mongorestore --uri "mongodb://localhost:27017" --db test_database database/test_database
```
Otherwise use the JSON fallback via the app: log in as admin → Website Settings → Restore.

## Production build (`frontend/build/`)

A pre-built static bundle is included (1070 KB). Deploy directly to any
static host — Netlify, Vercel, S3+CloudFront, or plain nginx.

**Important:** the bundle was built with
`REACT_APP_BACKEND_URL=(from .env)`.
If your backend runs on a different domain, rebuild with the correct value:

```bash
cd frontend
REACT_APP_BACKEND_URL=https://your-backend.com yarn build
```

### nginx example
```
server {
  listen 80;
  root /var/www/logisource/build;
  location / { try_files $uri /index.html; }
  location /api/ { proxy_pass http://backend:8001; }
}
```

## Security reminder
`backend/.env` contains JWT_SECRET, VAULT_MASTER_KEY, ADMIN_PASSWORD in cleartext.
ROTATE these before deploying to a public host.

## Seed credentials
- Admin: admin@logisource.com / Admin@12345
- Staff: staff@logisource.com / Staff@12345
