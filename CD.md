# Continuous Deployment (CD) — MimiPlay

CD automatically ships code to production after CI passes.
MimiPlay has two independent deployment targets:

| Target | Service | Workflow |
|--------|---------|----------|
| Frontend | AWS Amplify | `frontend.yml` |
| Backend + Monitoring | AWS EC2 (Docker Compose) | `backend.yml` + `monitoring.yml` |

---

## Architecture Overview

```
Developer pushes to main
        │
        ├──► GitHub Actions: frontend.yml
        │         └── Lint + Build → Trigger Amplify Job → Wait for SUCCEED
        │                              ↓
        │                    AWS Amplify builds React app
        │                    (reads VITE_API_URL from Amplify env vars)
        │                              ↓
        │                    Serves at https://main.djregh9s8o809.amplifyapp.com
        │
        └──► GitHub Actions: backend.yml
                  └── Python syntax check → SSH into EC2 → git pull → docker compose up --build
                                                ↓
                                    EC2 runs Docker Compose stack:
                                    Redis + PostgreSQL + Qdrant + Celery + Flask + Prometheus + Grafana
                                                ↓
                                    Nginx proxies HTTPS → Flask on port 5000
```

---

## Part 1 — Frontend Deployment (AWS Amplify)

### How it works

Amplify hosts the React app as a static site on a CDN. It does its own build on AWS servers and deploys to its global CDN automatically.

### One-time Amplify setup

1. Go to [AWS Amplify Console](https://console.aws.amazon.com/amplify)
2. Click **New app → Host web app**
3. Connect GitHub → select `abhiroy00/mimiplay` repository
4. Branch: `main`
5. Build settings — Amplify auto-detects Vite. Confirm the build command is `npm run build` and output directory is `dist`
6. Add environment variable before first build:
   - `VITE_API_URL` = `https://your-backend-domain.com` (your EC2 backend URL)
7. Click **Save and deploy**

### Amplify environment variables

Set these in **Amplify Console → Hosting → Environment variables → Manage variables**:

| Variable | Value | Purpose |
|----------|-------|---------|
| `VITE_API_URL` | `https://mimiplay.duckdns.org` | Backend API base URL baked into JS bundle |
| `AMPLIFY_MONOREPO_APP_ROOT` | `frontend` | Tells Amplify to build from the `frontend/` subfolder |
| `AMPLIFY_DIFF_DEPLOY` | `false` | Always do a full deploy (not diff-based) |

**Critical:** `VITE_API_URL` must be set BEFORE a build runs. If it is missing, Vite compiles `undefined` into every API call and the app cannot talk to the backend.

### GitHub Secrets for automated Amplify trigger (optional)

If you want GitHub Actions to trigger and monitor Amplify builds instead of Amplify auto-detecting pushes, add these secrets in **GitHub → Settings → Secrets → Actions**:

| Secret | Where to get it |
|--------|----------------|
| `AWS_ACCESS_KEY_ID` | AWS Console → IAM → Users → your user → Security credentials |
| `AWS_SECRET_ACCESS_KEY` | Same as above (shown once at creation) |
| `AWS_REGION` | e.g. `ap-south-1` (Mumbai) |
| `AMPLIFY_APP_ID` | Amplify Console URL: `apps/djregh9s8o809` → ID is `djregh9s8o809` |
| `VITE_API_URL_PRODUCTION` | Your backend HTTPS URL |
| `VITE_API_URL_STAGING` | Your staging backend URL |

Without these secrets, the deploy job is skipped (warning only) and Amplify uses its own auto-build from GitHub integration.

### What triggers a new Amplify build

- Push to `main` → Amplify auto-detects and builds (production)
- Push to `develop` → Amplify auto-detects and builds (staging, if branch connected)
- GitHub Actions triggers it via `aws amplify start-job` (if AWS secrets configured)
- Manual: Amplify Console → Deployments → **Redeploy this version** (reuses old artifacts — does NOT pick up new env vars)
- Manual fresh build: push a new commit or click **Run build** in Amplify Console

### Mixed Content problem and solution

Amplify serves the site over `https://`. If the backend URL is `http://`, browsers block the request with:
```
Mixed Content: The page was loaded over HTTPS but requested an insecure resource over HTTP. This request has been blocked.
```

**Solution:** The backend must also serve over HTTPS. See Part 2 — Nginx HTTPS setup.

---

## Part 2 — Backend Deployment (EC2 + Docker Compose)

### Docker Compose stack

All backend services run in Docker containers on a single EC2 instance:

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `mimi-redis` | `redis:7-alpine` | 6379 | Session cache + Celery broker |
| `mimi-postgres` | `postgres:15-alpine` | 5432 | Semantic memory (facts, knowledge) |
| `mimi-qdrant` | `qdrant/qdrant:latest` | 6333, 6334 | Vector database (episodic memory) |
| `mimi-celery-worker` | Custom (Dockerfile) | — | Background task processing |
| `mimi-app` | Custom (Dockerfile) | 5000 | Flask API server (Gunicorn + gevent) |
| `mimi-prometheus` | `prom/prometheus:v2.53.0` | 9090 | Metrics collection |
| `mimi-grafana` | `grafana/grafana:11.1.0` | 3000 | Metrics dashboard |

Nginx runs on the host (not in Docker) and proxies HTTPS → Flask port 5000.

### EC2 instance setup (one-time)

**Recommended specs:**
- AMI: Amazon Linux 2023
- Instance type: `t3.medium` (2 vCPU, 4 GB RAM minimum for this stack)
- Storage: 20 GB gp3

**Security Group inbound rules:**

| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 22 | TCP | Your IP | SSH access |
| 80 | TCP | 0.0.0.0/0 | HTTP (redirects to HTTPS via Nginx) |
| 443 | TCP | 0.0.0.0/0 | HTTPS (Nginx → Flask) |

Do NOT expose port 5000 publicly — Nginx proxies to it internally.

### Step-by-step EC2 first-time setup

**1. SSH into your EC2:**
```bash
ssh -i your-key.pem ec2-user@YOUR_EC2_IP
```

**2. Install Docker:**
```bash
sudo dnf install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
exit  # logout so group applies
ssh -i your-key.pem ec2-user@YOUR_EC2_IP
docker ps  # verify
```

**3. Install Docker Compose (Amazon Linux 2023 manual install):**
```bash
mkdir -p ~/.docker/cli-plugins/
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o ~/.docker/cli-plugins/docker-compose
chmod +x ~/.docker/cli-plugins/docker-compose
docker compose version
```

**4. Install Docker Buildx (required for building custom images):**
```bash
mkdir -p ~/.docker/cli-plugins
curl -SL https://github.com/docker/buildx/releases/download/v0.17.1/buildx-v0.17.1.linux-amd64 \
  -o ~/.docker/cli-plugins/docker-buildx
chmod +x ~/.docker/cli-plugins/docker-buildx
docker buildx version
```

**5. Install Git and clone the repo:**
```bash
sudo dnf install -y git
sudo mkdir -p /opt/mimiplay
sudo chown ec2-user:ec2-user /opt/mimiplay
git clone https://github.com/abhiroy00/mimiplay.git /opt/mimiplay
```

**6. Create the `.env` file:**
```bash
nano /opt/mimiplay/backend/.env
```

Paste and fill in your real values:
```env
# Required
MONGODB_URI=mongodb+srv://USERNAME:PASSWORD@cluster.mongodb.net/mimidb
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
SECRET=any-long-random-string-for-jwt-signing

# Optional
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx
YOUTUBE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxx

# Auto-configured by Docker Compose (do not change)
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql://postgres:mimipass@postgres:5432/mimidb
QDRANT_URL=http://qdrant:6333
USE_ADVANCED_MEMORY=false
USE_CELERY=true
ENABLE_RESPONSE_CACHE=true
POSTGRES_PASSWORD=mimipass
```

**7. Start the Docker stack:**
```bash
cd /opt/mimiplay/backend
docker compose up -d
docker compose ps  # all should show "running" or "healthy"
docker compose logs app --tail=30  # check Flask started OK
curl http://localhost:5000/health  # should return {"status":"ok"}
```

---

## Part 3 — HTTPS Setup (Nginx + Let's Encrypt)

This is required because Amplify serves over `https://` and browsers block HTTP backend calls from HTTPS pages (Mixed Content policy).

### Step 1 — Get a free domain from DuckDNS

1. Go to [duckdns.org](https://www.duckdns.org) and sign in with Google
2. Enter a subdomain name (e.g. `mimiplay`) → click **Add domain**
3. Set the IP to your EC2 public IP → click **Update IP**
4. Your backend is now reachable at `mimiplay.duckdns.org`

**Important:** Every time EC2 stops and restarts, the public IP changes. Either:
- Update DuckDNS IP manually each time, OR
- Allocate an **Elastic IP** in AWS Console → EC2 → Elastic IPs → Associate with instance (permanent IP, small cost)

### Step 2 — Install Nginx and Certbot on EC2

```bash
sudo dnf install -y nginx python3-certbot-nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Step 3 — Get the SSL certificate

```bash
# Replace mimiplay with YOUR duckdns subdomain
sudo certbot --nginx -d mimiplay.duckdns.org \
  --non-interactive --agree-tos \
  -m your-email@gmail.com
```

Certbot automatically edits the Nginx config to add SSL. Certificate is valid for 90 days and auto-renews.

### Step 4 — Configure Nginx as reverse proxy

```bash
sudo tee /etc/nginx/conf.d/mimi.conf << 'EOF'
server {
    listen 443 ssl;
    server_name mimiplay.duckdns.org;

    ssl_certificate     /etc/letsencrypt/live/mimiplay.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mimiplay.duckdns.org/privkey.pem;

    location / {
        proxy_pass         http://localhost:5000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-Proto https;
    }
}

server {
    listen 80;
    server_name mimiplay.duckdns.org;
    return 301 https://$host$request_uri;
}
EOF

sudo nginx -t          # test config
sudo systemctl reload nginx
```

**Test it:**
```bash
curl https://mimiplay.duckdns.org/health
```

### Step 5 — Update Amplify environment variable

In **Amplify Console → Hosting → Environment variables → Manage variables**:

Change `VITE_API_URL` from:
```
http://OLD_EC2_IP:5000
```
to:
```
https://mimiplay.duckdns.org
```

Then push a commit to trigger a fresh Amplify build:
```bash
git commit --allow-empty -m "trigger: fresh build with HTTPS backend URL"
git push origin main
```

---

## Part 4 — Automated Deployment via GitHub Actions

Once all secrets are configured, every push to `main` runs the full automated pipeline:

### GitHub Secrets required for full automation

Go to **GitHub repo → Settings → Secrets and variables → Actions → New repository secret**:

**Backend deploy secrets:**

| Secret | Value |
|--------|-------|
| `EC2_HOST_PRODUCTION` | Your EC2 public IP (e.g. `65.0.96.68`) or DuckDNS domain |
| `EC2_USER_PRODUCTION` | `ec2-user` (Amazon Linux) |
| `EC2_SSH_KEY_PRODUCTION` | Full contents of your `.pem` file (open in Notepad, copy everything) |
| `EC2_HOST_STAGING` | Staging EC2 IP (if you have one) |
| `EC2_USER_STAGING` | `ec2-user` |
| `EC2_SSH_KEY_STAGING` | Staging EC2 `.pem` file contents |

**Frontend deploy secrets:**

| Secret | Value |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | From AWS IAM user |
| `AWS_SECRET_ACCESS_KEY` | From AWS IAM user |
| `AWS_REGION` | `ap-south-1` |
| `AMPLIFY_APP_ID` | From Amplify Console URL (e.g. `djregh9s8o809`) |
| `VITE_API_URL_PRODUCTION` | `https://mimiplay.duckdns.org` |
| `VITE_API_URL_STAGING` | Staging backend URL |

### Automated pipeline flow on `git push origin main`

```
git push origin main
        │
        ├──► frontend.yml triggered (frontend/** changed)
        │         ├── CI: npm run lint → npm run build (with VITE_API_URL_PRODUCTION)
        │         └── CD: aws amplify start-job → polls until SUCCEED/FAILED
        │
        ├──► backend.yml triggered (backend/** changed)
        │         ├── CI: python -m py_compile app.py ...
        │         └── CD: SSH to EC2 → git pull → docker compose up -d --build
        │
        └──► monitoring.yml triggered (monitoring/** changed)
                  └── SSH to EC2 → curl Prometheus reload → docker restart Grafana
```

### Graceful degradation when secrets are not configured

All three workflows use a pre-check pattern: if a required secret is empty, the deploy step is **skipped with a warning** (not a failure). This means:
- CI (lint/build/syntax check) always runs
- Deploy is silently skipped if not yet configured
- The pipeline shows green so you can merge code without having secrets set up

---

## Part 5 — Monitoring (Prometheus + Grafana)

Prometheus and Grafana run as Docker containers inside the same `docker-compose.yml` stack as the Flask app.

**Prometheus** scrapes metrics from Flask at `http://mimi-app:5000/metrics` every 15 seconds.

**Grafana** displays dashboards. Default login: `admin` / `changeme` (set `GRAFANA_ADMIN_PASSWORD` in `.env` to change).

### Accessing dashboards (port-forward from EC2)

Grafana is not exposed publicly. To view it, create an SSH tunnel:
```bash
ssh -i your-key.pem -L 3000:localhost:3000 ec2-user@YOUR_EC2_IP
```
Then open `http://localhost:3000` in your browser.

### Updating monitoring config

Edit `monitoring/prometheus/prometheus.yml` or Grafana dashboard JSONs in `monitoring/grafana/`, then push to `main`. The `monitoring.yml` workflow SSHs into EC2 and hot-reloads Prometheus without restarting the whole stack.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `undefined/api/login` on live site | `VITE_API_URL` not set at build time | Set env var in Amplify Console, trigger fresh build |
| `Mixed Content` error in browser | Backend is `http://`, frontend is `https://` | Set up Nginx + Let's Encrypt (Part 3) |
| `Failed to fetch` on login | EC2 stopped → new IP, or Docker not running | SSH in, `docker compose up -d`, update DuckDNS IP |
| `compose build requires buildx 0.17.0` | Docker Buildx too old on EC2 | Install newer Buildx manually (Part 2, Step 4) |
| `No match for argument: docker-compose-plugin` | Amazon Linux 2023 doesn't have it in dnf | Install Docker Compose as CLI plugin manually (Part 2, Step 3) |
| Backend deploy skipped with warning | `EC2_HOST_PRODUCTION` secret not set | Add EC2 secrets in GitHub repo settings |
| Amplify deploy skipped with warning | AWS secrets not set | Add `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AMPLIFY_APP_ID` |
| EC2 IP changes after restart | No Elastic IP assigned | Allocate Elastic IP in AWS Console and associate with instance |
