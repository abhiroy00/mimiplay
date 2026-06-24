# Start Mimi After AWS Restart

Every time you stop/restart the EC2 instance, follow these 4 steps.

---

## Step 1 — SSH into EC2

Open PowerShell on your Windows machine and run:

```powershell
ssh -i C:\Users\sharm\Downloads\mimi-key.pem ec2-user@YOUR_NEW_EC2_IP
```

> Get the new IP from: **AWS Console → EC2 → Instances → your instance → Public IPv4 address**
> The IP changes every restart unless you have an Elastic IP.

---

## Step 2 — Start Docker (backend + database + all services)

```bash
cd /opt/mimiplay/backend
docker compose up -d
docker compose ps
```

All containers should show **running**. If something is wrong:

```bash
docker compose logs app --tail=30
```

---

## Step 3 — Start ngrok tunnel (HTTPS for frontend)

```bash
nohup ngrok http --url=daybreak-monstrous-starving.ngrok-free.dev 5000 > ~/ngrok.log 2>&1 &
sleep 3
cat ~/ngrok.log
```

You should see:
```
Forwarding  https://daybreak-monstrous-starving.ngrok-free.dev -> http://localhost:5000
```

---

## Step 4 — Verify everything is live

```bash
curl https://daybreak-monstrous-starving.ngrok-free.dev/health
```

If you get a JSON response, Mimi is running.
Open your browser: **https://main.djregh9s8o809.amplifyapp.com** — it should work.

---

## Quick reference (copy-paste all at once after SSH)

```bash
cd /opt/mimiplay/backend && docker compose up -d
nohup ngrok http --url=daybreak-monstrous-starving.ngrok-free.dev 5000 > ~/ngrok.log 2>&1 &
sleep 3 && curl https://daybreak-monstrous-starving.ngrok-free.dev/health
```

---

## Shutdown (before stopping EC2 to save money)

```bash
cd /opt/mimiplay/backend && docker compose down
pkill ngrok
```
