<h1 align="center">💇 HairStyle AI</h1>

<p align="center">
  <strong>AI-powered face shape analysis & personalised hairstyle + beard style recommendations</strong><br/>
  Built with Python · Flask · MediaPipe · MongoDB · Gemini · Replicate
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/Flask-2.3-black?style=for-the-badge&logo=flask" />
  <img src="https://img.shields.io/badge/MongoDB-Atlas-green?style=for-the-badge&logo=mongodb" />
  <img src="https://img.shields.io/badge/MediaPipe-0.10-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Deployed%20on-Render-46E3B7?style=for-the-badge&logo=render" />
</p>

---

## 🌟 Overview

**HairStyle AI** is a web application that analyses a user's face shape from a photo and instantly recommends the most flattering hairstyles and beard styles. It uses Google's MediaPipe to detect 468 facial landmarks, classifies the face shape, and provides curated style recommendations — complete with an **AR Try-On** feature powered by Replicate's image generation API.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📸 **Face Shape Analysis** | Upload a photo — AI detects your face shape (Oval, Round, Square, Heart, Diamond, Oblong) |
| 💇 **Hairstyle Recommendations** | Get personalised hairstyle suggestions tailored to your face shape |
| 🧔 **Beard Style Recommendations** | Beard style recommendations matched to your facial structure |
| 🪞 **AR Try-On** | Virtually try styles on your webcam feed using AI-generated overlays |
| 🤖 **AI Chatbot** | Built-in rule-based chatbot to guide users |
| 📜 **Analysis History** | Every analysis is saved to your personal dashboard |
| 🔐 **Auth System** | Secure register/login with bcrypt password hashing |
| 🎭 **Auto Gender Detection** | Gemini Flash Lite auto-detects gender from the uploaded photo |

---

## 🛠️ Tech Stack

```
Backend    : Python 3.10+, Flask 2.3, Gunicorn
AI/CV      : MediaPipe 0.10, OpenCV (headless), TensorFlow 2.13, DeepFace
APIs       : Google Gemini Flash Lite (gender detection), Replicate (AR style generation)
Database   : MongoDB (Atlas for cloud, localhost for dev)
Auth       : Flask-Bcrypt, Flask-Login
Frontend   : Vanilla HTML/CSS/JS (Jinja2 templates)
Deployment : Render (render.yaml included)
```

---

## 🖥️ Screenshots

> Upload your photo → get your face shape → see personalised style recommendations → try them on live via AR.

---

## 🚀 Getting Started (Local)

### Prerequisites
- Python 3.10+
- MongoDB running locally (`mongod`)
- A Gemini API key ([get one free](https://makersuite.google.com/app/apikey))
- A Replicate API token ([get one free](https://replicate.com))

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/hairstyle-ai.git
cd hairstyle-ai
```

### 2. Create a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
cp .env.example .env
```
Edit `.env` and fill in your values:
```env
SECRET_KEY=your_random_secret_key
MONGO_URI=mongodb://localhost:27017/hair_beard_ai
GEMINI_API_KEY=your_gemini_api_key
REPLICATE_API_TOKEN=your_replicate_token
DEBUG=True
```

### 5. Run the app
```bash
python app.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## ☁️ Deploying to Render

This repo includes a `render.yaml` for one-click deployment.

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — review settings and confirm
5. Add these **Environment Variables** in the Render dashboard:

| Variable | Value |
|----------|-------|
| `SECRET_KEY` | Any random 32-char string |
| `MONGO_URI` | Your MongoDB Atlas connection URI |
| `GEMINI_API_KEY` | Your Gemini API key |
| `REPLICATE_API_TOKEN` | Your Replicate token |
| `DEBUG` | `False` |

6. Click **Deploy** — your app will be live in ~3 minutes ✅

> **MongoDB Atlas:** For cloud deployment, use a free [MongoDB Atlas](https://cloud.mongodb.com) cluster. Make sure to whitelist `0.0.0.0/0` in Network Access.

---

## 📁 Project Structure

```
hairstyle-ai/
│
├── app.py                  # Application factory
├── wsgi.py                 # Gunicorn/WSGI entry point
├── config.py               # Configuration (reads from .env)
├── database.py             # MongoDB connection module
│
├── routes/
│   ├── auth.py             # Register, Login, Logout
│   ├── analysis.py         # Face analysis, AR snapshot, history
│   └── chatbot.py          # AI chatbot API endpoint
│
├── utils/
│   ├── face_utils.py       # MediaPipe face landmark analysis
│   ├── gender_detector.py  # Gemini-based gender auto-detection
│   ├── style_preview.py    # AR Try-On rendering (Replicate + OpenCV)
│   └── style_recommender.py# Face-shape → style mapping engine
│
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS, JS, images, uploads
│
├── requirements.txt        # Python dependencies
├── Procfile                # Render/Heroku start command
├── render.yaml             # Render deployment config
└── .env.example            # Environment variable template
```

---

## 🔐 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | Flask session secret (use a long random string) |
| `MONGO_URI` | ✅ | MongoDB connection URI |
| `GEMINI_API_KEY` | ✅ | Google Gemini API key for gender detection |
| `REPLICATE_API_TOKEN` | ✅ | Replicate token for AR image generation |
| `UPLOAD_FOLDER` | ❌ | Default: `static/uploads` |
| `MAX_CONTENT_LENGTH` | ❌ | Default: `16777216` (16 MB) |
| `DEBUG` | ❌ | Default: `False` (set `True` for local dev) |

---

## 👤 Author

**S. Thiruselvam** (Roll No: 23COS263)  
AI-powered personal styling assistant — built as a final-year project using Python, Flask, MediaPipe, and MongoDB.

---

## 📄 License

This project is for educational purposes. All rights reserved © 2024 S. Thiruselvam.
