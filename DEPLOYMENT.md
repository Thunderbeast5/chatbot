# AI For Her - Chatbot Backend Deployment Guide

## 🚀 Deploy to Render

### Prerequisites
- GitHub account
- Render account (free tier works!)
- Groq API key

### Step 1: Initialize Git Repository

```bash
cd chatbot1
git init
git add .
git commit -m "Initial chatbot backend"
```

### Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository: `AI-For-Her-Chatbot`
3. Don't initialize with README (we already have files)

### Step 3: Push to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/AI-For-Her-Chatbot.git
git branch -M main
git push -u origin main
```

### Step 4: Deploy on Render

1. Go to https://render.com
2. Sign up/Login with GitHub
3. Click **"New +"** → **"Web Service"**
4. Connect your `AI-For-Her-Chatbot` repository
5. Configure:
   - **Name**: `ai-for-her-chatbot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: `Free`

### Step 5: Add Environment Variables

In Render dashboard, go to **Environment** tab and add:

```
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_api_key_here (optional)
OPENAI_API_KEY=your_openai_api_key_here (optional)
```

**Note**: Use your actual API keys from:
- Groq: https://console.groq.com/keys
- Google: https://makersuite.google.com/app/apikey
- OpenAI: https://platform.openai.com/api-keys

### Step 6: Deploy!

Click **"Create Web Service"** and wait 5-10 minutes for deployment.

### Step 7: Get Your API URL

After deployment, you'll get a URL like:
```
https://ai-for-her-chatbot.onrender.com
```

### Step 8: Update React Frontend

Update `src/pages/Chat.jsx`:

```javascript
const CHATBOT_API_URL = 'https://ai-for-her-chatbot.onrender.com/api/chat'
```

### Step 9: Update CORS in app.py

Make sure your deployed backend allows your frontend domain:

```python
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5173",
            "https://your-react-app.netlify.app",  # Add your deployed frontend URL
            "https://ai-for-her.onrender.com"
        ]
    }
})
```

## 🧪 Test Your Deployment

Test the health endpoint:
```bash
curl https://ai-for-her-chatbot.onrender.com/api/health
```

Should return:
```json
{"status": "ok", "message": "Chatbot API is running"}
```

## 📝 Important Notes

1. **Free Tier Limitations**:
   - Service spins down after 15 minutes of inactivity
   - First request after spin-down takes 30-60 seconds
   - Upgrade to paid plan ($7/month) for always-on service

2. **Database**:
   - SQLite works on Render but data resets on redeploy
   - For production, consider PostgreSQL (Render offers free tier)

3. **API Keys**:
   - Never commit `.env` file
   - Always use Render's environment variables

## 🔄 Redeploy After Changes

```bash
git add .
git commit -m "Update chatbot"
git push origin main
```

Render will auto-deploy on push!

## 🐛 Troubleshooting

**Build fails?**
- Check `requirements.txt` for typos
- Ensure Python version is 3.11

**App crashes?**
- Check Render logs
- Verify environment variables are set
- Test locally first: `gunicorn app:app`

**CORS errors?**
- Update CORS origins in `app.py`
- Redeploy after changes

## 📞 Support

If you face issues, check:
- Render logs (in dashboard)
- Browser console (for frontend errors)
- Network tab (for API requests)
