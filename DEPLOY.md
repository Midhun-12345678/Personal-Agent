# Deploying Nanobot to Railway.app

This guide covers deploying Nanobot (backend + frontend) to Railway's free tier for public access.

## Prerequisites

- A Railway account (free tier available)
- Railway CLI installed
- Git repository with your Nanobot code
- LLM API keys (Anthropic, OpenAI, etc.)
- Google OAuth credentials (for Gmail/Calendar integration)

## Architecture

The deployment consists of two services:
- **Backend**: FastAPI + Python 3.11 (port 8765)
- **Frontend**: Next.js 14 (port 3000)

## Step 1: Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Click "Sign up" and use GitHub OAuth
3. Free tier includes:
   - $5/month credit
   - 512 MB RAM per service
   - Shared CPU
   - Public URL with SSL

## Step 2: Install Railway CLI

```bash
# macOS/Linux
brew install railway

# npm (all platforms)
npm install -g @railway/cli

# Verify installation
railway --version
```

Login to Railway:
```bash
railway login
```

## Step 3: Deploy Backend Service

### 3.1 Create New Project

```bash
# From your nanobot directory
cd d:/Nanobot/nanobot

# Initialize Railway project
railway init
```

Choose "Create new project" and name it `nanobot-backend`.

### 3.2 Link to Railway Project

```bash
railway link
```

Select the project you just created.

### 3.3 Set Environment Variables

```bash
# Required: LLM API keys
railway variables set ANTHROPIC_API_KEY="your-key-here"

# Optional: Other providers
railway variables set OPENAI_API_KEY="your-key-here"
railway variables set GROQ_API_KEY="your-key-here"

# Optional: Web search
railway variables set BRAVE_API_KEY="your-key-here"

# Required: Google OAuth (get these from Google Cloud Console)
railway variables set GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
railway variables set GOOGLE_CLIENT_SECRET="your-client-secret"

# Optional: Workspace path (defaults to /app/.personal-agent in container)
railway variables set NANOBOT_WORKSPACE="/app/.personal-agent"
```

Or set them via the Railway Dashboard:
1. Go to your project dashboard
2. Click on the service
3. Go to "Variables" tab
4. Add variables one by one

### 3.4 Deploy Backend

```bash
railway up
```

Railway will:
- Build the Docker image using your `Dockerfile`
- Deploy to a public URL (e.g., `https://nanobot-backend-production.up.railway.app`)
- Start the service with `python run.py`

### 3.5 Get Backend Public URL

```bash
railway domain
```

Or find it in the Railway Dashboard → Service → Settings → Domains.

Example: `https://nanobot-backend-production.up.railway.app`

## Step 4: Deploy Frontend Service

### 4.1 Create Frontend Service

From the frontend directory:

```bash
cd frontend
railway init
```

Choose your existing project (`nanobot`), then "Create new service" named `nanobot-frontend`.

### 4.2 Set Frontend Environment Variables

```bash
# Use the backend URL from Step 3.5
railway variables set NEXT_PUBLIC_API_URL="https://nanobot-backend-production.up.railway.app"

# WebSocket URL (use wss:// for HTTPS)
railway variables set NEXT_PUBLIC_WS_URL="wss://nanobot-backend-production.up.railway.app"
```

### 4.3 Deploy Frontend

```bash
railway up
```

### 4.4 Get Frontend Public URL

```bash
railway domain
```

Example: `https://nanobot-frontend-production.up.railway.app`

## Step 5: Configure Google OAuth for Public URLs

Now that you have public URLs, you need to update Google OAuth redirect URIs.

### 5.1 Update Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Select your OAuth 2.0 Client ID
3. Under "Authorized redirect URIs", add:
   ```
   https://nanobot-backend-production.up.railway.app/integrations/callback
   ```
4. Save changes

### 5.2 Update config.json (if needed)

If you're using a local `config.json` that gets deployed, update it with your Google OAuth credentials:

```json
{
  "integrations": {
    "google": {
      "clientId": "YOUR_CLIENT_ID.apps.googleusercontent.com",
      "clientSecret": "YOUR_CLIENT_SECRET"
    }
  },
  "agents": {
    "defaults": {
      "model": "claude-sonnet-4-20250514",
      "provider": "anthropic"
    }
  },
  "providers": {
    "anthropic": {
      "apiKey": "sk-ant-..."
    }
  }
}
```

Alternatively, set these in Railway environment variables (preferred for security):

```bash
railway variables set GOOGLE_CLIENT_ID="your-id"
railway variables set GOOGLE_CLIENT_SECRET="your-secret"
```

## Step 6: Access Your Deployed App

1. Open your frontend URL: `https://nanobot-frontend-production.up.railway.app`
2. Register an account
3. Start chatting!

## Step 7: Enable Data Persistence (Optional)

Railway ephemeral storage is wiped on every deploy. To persist data:

### Option 1: Use Railway Volumes (Recommended)

```bash
# Create a volume for the backend service
railway volume create

# Mount at /app/.personal-agent (where NANOBOT_WORKSPACE points)
railway volume attach /app/.personal-agent
```

### Option 2: Use External Database

For production, consider:
- **PostgreSQL** for user data, sessions
- **S3** for file storage
- **Redis** for ChromaDB (or use external ChromaDB service)

Update your code to use these external services instead of local files.

## Monitoring and Logs

### View Logs

```bash
# Backend logs
railway logs

# Frontend logs (from frontend directory)
cd frontend && railway logs
```

### View in Dashboard

1. Go to Railway Dashboard
2. Click on your service
3. Go to "Deployments" tab
4. Click on active deployment to see logs

## Troubleshooting

### Backend not starting

Check logs:
```bash
railway logs
```

Common issues:
- Missing API keys → Set environment variables
- Port binding → Railway automatically assigns PORT variable
- Dockerfile errors → Check build logs

### Frontend can't connect to backend

1. Verify NEXT_PUBLIC_API_URL is set correctly:
   ```bash
   railway variables
   ```

2. Check if backend is running:
   ```bash
   curl https://your-backend-url.railway.app/health
   ```

3. CORS issues → Backend should allow your frontend domain

### OAuth errors

1. Verify redirect URI in Google Cloud Console matches exactly:
   ```
   https://your-backend-url.railway.app/integrations/callback
   ```

2. Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set:
   ```bash
   railway variables
   ```

### Out of memory

Free tier has 512MB RAM limit. Monitor usage:
- Railway Dashboard → Service → Metrics

Optimizations:
- Reduce model context size
- Limit ChromaDB collection size
- Use smaller sentence-transformer models

## Cost Optimization

### Free Tier Limits
- $5/month credit (resets monthly)
- ~550 hours of uptime (512MB RAM service)
- If you exceed, service will pause until next month

### Tips to Stay Free
1. Use **sleep on inactivity** (Railway can auto-sleep after 10min idle)
2. Use smaller models (claude-haiku-4-20250514 instead of opus)
3. Limit web searches (Brave API has rate limits)
4. Use external ChromaDB (free tier available)

## Updating Your Deployment

### Update Backend

```bash
# From backend directory
git pull  # or make local changes
railway up
```

### Update Frontend

```bash
# From frontend directory
git pull  # or make local changes
railway up
```

### Rolling Back

```bash
# View deployments
railway status

# Rollback to previous deployment
railway rollback <deployment-id>
```

## Custom Domain (Optional)

### Add Custom Domain

1. Go to Railway Dashboard
2. Click on service (frontend or backend)
3. Settings → Domains
4. Click "Add Domain"
5. Enter your domain (e.g., `nanobot.yourdomain.com`)
6. Add DNS records to your domain provider:
   - **Type**: CNAME
   - **Name**: nanobot (or your subdomain)
   - **Value**: (provided by Railway)

Railway automatically provisions SSL certificates.

## Security Best Practices

1. **Never commit API keys** to git
   - Use Railway environment variables
   - Add `.env` to `.gitignore`

2. **Use strong passwords** for user accounts
   - Backend has bcrypt password hashing

3. **Enable HTTPS only**
   - Railway provides SSL by default
   - Update OAuth redirect URIs to use `https://`

4. **Rate limiting** (optional)
   - Add rate limiting middleware to prevent abuse

5. **Monitor logs** for suspicious activity

## Next Steps

- Set up monitoring (e.g., Sentry for error tracking)
- Add analytics (e.g., PostHog, Plausible)
- Configure backups for persistent data
- Set up CI/CD with GitHub Actions
- Add more integrations (Slack, Discord, etc.)

## Support

If you encounter issues:
1. Check Railway Dashboard logs
2. Review this guide carefully
3. Consult Railway docs: [docs.railway.app](https://docs.railway.app)
4. Open an issue on GitHub

## Example Environment Variables

Here's a complete list of environment variables you might need:

**Backend Service:**
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-xxxx
GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxx

# Optional
PORT=8765  # Auto-set by Railway
NANOBOT_WORKSPACE=/app/.personal-agent
OPENAI_API_KEY=sk-proj-xxxx
GROQ_API_KEY=gsk_xxxx
BRAVE_API_KEY=BSA-xxxx
```

**Frontend Service:**
```bash
# Required
NEXT_PUBLIC_API_URL=https://nanobot-backend-production.up.railway.app
NEXT_PUBLIC_WS_URL=wss://nanobot-backend-production.up.railway.app

# Optional (auto-set by Railway)
PORT=3000
```

---

**Congratulations!** Your Nanobot is now live and accessible to anyone with the public URL! 🎉
