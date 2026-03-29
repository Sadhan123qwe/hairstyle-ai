from flask import Blueprint, request, jsonify
import re
import datetime

chatbot_bp = Blueprint('chatbot', __name__)

# ═══════════════════════════════════════════════════════════
#  HairStyle AI – Smart Rule-Based Chatbot Engine
# ═══════════════════════════════════════════════════════════

KNOWLEDGE_BASE = [
    # ── Greetings ──
    {
        'patterns': [r'\b(hi|hello|hey|hiya|good morning|good evening|good afternoon|howdy|greetings)\b'],
        'responses': [
            "Hello! 👋 Welcome to HairStyle AI! I'm your personal style assistant. Ask me anything about hairstyles, beard styles, face shapes, or how to use the app.",
            "Hey there! 😊 I'm the HairStyle AI assistant. I can help you with hairstyle recommendations, face shape info, or guide you through using the app!",
            "Hi! Great to see you here! 💇 Ask me anything about hair & beard styles or what your face shape means."
        ]
    },

    # ── What is this app ──
    {
        'patterns': [r'\b(what is|about|tell me about|explain|describe).*(app|website|hairstyle ai|this site|this platform)\b',
                     r'\b(what does this|how does this).*(work|do)\b'],
        'responses': [
            "🌟 **HairStyle AI** is an AI-powered web app that analyses your face shape from a photo and recommends the best hairstyles and beard styles for you! \n\n📸 You upload your photo → our AI detects your facial landmarks → and you get personalised recommendations instantly."
        ]
    },

    # ── How to use / get started ──
    {
        'patterns': [r'\b(how (to|do i|can i)|how to use|get started|begin|start|use the app)\b'],
        'responses': [
            "It's super simple! Here's how to get started:\n\n1️⃣ **Register** or **Log in**\n2️⃣ Click on **Analyze** in the navigation bar\n3️⃣ **Upload** a clear, front-facing photo\n4️⃣ Select your gender preference\n5️⃣ Hit **Analyze My Face Shape**\n\nYou'll instantly get personalised hairstyle & beard recommendations! 🎉"
        ]
    },

    # ── Face shapes ──
    {
        'patterns': [r'\b(face shape|oval face|round face|square face|heart face|diamond face|oblong face)\b'],
        'responses': [
            "Great question! There are **6 main face shapes**:\n\n🟡 **Oval** – Balanced proportions, suits almost any style\n⭕ **Round** – Wide cheeks, shorter length; angular cuts work well\n⬛ **Square** – Strong jaw & forehead; softer styles balance features\n❤️ **Heart** – Wider forehead, narrow chin; side-swept styles look great\n💠 **Diamond** – Narrow forehead & chin, wide cheeks; volume on top helps\n📏 **Oblong** – Longer face; avoid styles adding extra height\n\nUpload your photo and our AI identifies yours automatically! 📸"
        ]
    },
    {
        'patterns': [r'\b(oval)\b.*\b(face|shape)\b', r'\b(face|shape)\b.*\b(oval)\b'],
        'responses': [
            "✨ **Oval Face Shape** is considered the most balanced and versatile face shape! Almost any hairstyle works for you.\n\n🏆 **Best hairstyles:** Classic Pompadour, Side Part, Textured Quiff, Buzz Cut, Slick Back\n🧔 **Beard styles:** Full Beard, Short Boxed Beard, Circle Beard all suit you perfectly!"
        ]
    },
    {
        'patterns': [r'\b(round)\b.*\b(face|shape)\b', r'\b(face|shape)\b.*\b(round)\b'],
        'responses': [
            "⭕ **Round Face Shape** has equal width and length with soft, curved features.\n\n💡 Aim for styles that **add height and angularity**:\n🏆 **Best hairstyles:** High Fade with Volume, Pompadour, Mohawk, Angular Fringe\n🧔 **Beard styles:** Goatee, Extended Goatee, Van Dyke – these elongate the face!"
        ]
    },
    {
        'patterns': [r'\b(square)\b.*\b(face|shape)\b', r'\b(face|shape)\b.*\b(square)\b'],
        'responses': [
            "⬛ **Square Face Shape** has a strong jawline and broad forehead with angular features.\n\n💡 Go for **softer, textured styles** to balance the angles:\n🏆 **Best hairstyles:** Textured Crop, Quiff, Messy Fringe, Side Part\n🧔 **Beard styles:** Short Stubble, Circle Beard work best to soften the jaw"
        ]
    },

    # ── Hairstyles ──
    {
        'patterns': [r'\b(hairstyle|haircut|hair style|hair cut|hair recommendation|best hair)\b'],
        'responses': [
            "💇 Our AI recommends hairstyles based on **your specific face shape**!\n\nSome popular styles we recommend:\n\n✂️ **Classic Pompadour** – Sweep hair upward & back for a timeless polished look\n✂️ **Side Part** – Clean side part with longer top and shorter sides\n✂️ **Textured Quiff** – Textured styling lifted at the front for volume\n✂️ **Buzz Cut** – Uniform short cut, great for balanced oval shapes\n✂️ **Slick Back** – All hair combed back smooth for a sleek appearance\n\nUpload your photo to get recommendations tailored to **you** specifically! 📸"
        ]
    },

    # ── Beard styles ──
    {
        'patterns': [r'\b(beard|beard style|facial hair|beard recommendation|best beard|stubble|goatee|moustache|mustache)\b'],
        'responses': [
            "🧔 Great question about beard styles! Our AI recommends beards based on your face shape.\n\nPopular beard styles we suggest:\n\n🟫 **Full Beard** – A full, well-groomed beard for a masculine look\n🟫 **Short Boxed Beard** – Neat and close to the face with defined edges\n🟫 **Circle Beard** – Round goatee shape for a balanced appearance\n🟫 **Stubble** – Light stubble for a rugged, casual look\n🟫 **Van Dyke** – Combo of moustache and goatee\n\nTry the **Analyze** feature to get your personalised beard recommendations! 🎯"
        ]
    },

    # ── Photo tips ──
    {
        'patterns': [r'\b(photo|picture|image|selfie|upload|tip|tips|lighting|clear)\b'],
        'responses': [
            "📸 Here are tips for the **best results**:\n\n✅ Use a clear, well-lit **front-facing photo**\n✅ Look **directly at the camera**\n✅ Avoid heavy shadows on your face\n✅ Make sure your **full face is visible**\n✅ Pull back hair to expose your natural face shape\n✅ Avoid sunglasses or heavy accessories\n\nGood lighting + straight-on angle = most accurate AI analysis! 💡"
        ]
    },

    # ── Account / login / register ──
    {
        'patterns': [r'\b(login|log in|sign in|register|sign up|create account|account)\b'],
        'responses': [
            "🔐 To use HairStyle AI's personalized recommendations:\n\n📝 **New user?** Click **Get Started** or visit the Register page to create a free account.\n🔑 **Already have an account?** Click **Login** in the navigation bar.\n\nOnce logged in, you can:\n- Analyze your face shape\n- View your analysis history\n- Access your personal dashboard 📊"
        ]
    },

    # ── History / past results ──
    {
        'patterns': [r'\b(history|past (result|analysis|analysis)|previous|my result)\b'],
        'responses': [
            "📜 Your **Analysis History** is saved automatically every time you analyze a photo!\n\nTo view it:\n1. Make sure you're **logged in**\n2. Click **History** in the navigation bar\n3. See all your previous face shape analyses and recommendations\n\nYour history is private and only visible to you 🔒"
        ]
    },

    # ── Technology ──
    {
        'patterns': [r'\b(technology|tech|ai|mediapipe|opencv|flask|mongodb|how does the ai|machine learning|computer vision)\b'],
        'responses': [
            "⚙️ HairStyle AI is powered by cutting-edge technology:\n\n🧠 **MediaPipe** – Google's AI framework for real-time face landmark detection (468 points!)\n🐍 **Flask** – Python web framework for the backend\n🍃 **MongoDB** – Database for user accounts and history\n👁️ **OpenCV** – Computer vision for image processing\n📐 **Custom algorithms** – For face shape classification based on facial measurements\n\nAll processing happens on our server – your photos are analyzed securely 🔒"
        ]
    },

    # ── Free / cost ──
    {
        'patterns': [r'\b(free|cost|price|paid|subscription|money|charge)\b'],
        'responses': [
            "🎉 **HairStyle AI is completely FREE to use!**\n\nYou can:\n✅ Create an account for free\n✅ Analyze unlimited photos\n✅ Get personalised hairstyle & beard recommendations\n✅ View your full analysis history\n\nNo hidden charges, no subscriptions – just great style recommendations! 💇"
        ]
    },

    # ── Privacy / data ──
    {
        'patterns': [r'\b(privacy|data|secure|security|safe|photo stored|delete|personal)\b'],
        'responses': [
            "🔒 **Your privacy matters to us!**\n\n- Your uploaded photos are processed on our secure server\n- Analysis results are saved to your personal account only\n- We do not share your data with third parties\n- You can view your history and data anytime from your Dashboard\n\nFeel free to use HairStyle AI with confidence! 🛡️"
        ]
    },

    # ── Error / not working ──
    {
        'patterns': [r'\b(error|not working|broken|bug|issue|problem|fail|crash|wrong)\b'],
        'responses': [
            "😟 Sorry to hear things aren't working! Here are some quick fixes:\n\n🔄 **Try refreshing** the page\n📸 **Check your photo** – make sure it's a clear front-facing image (JPG/PNG, max 16MB)\n🌐 **Check your connection** – the app needs internet to load\n🔑 **Log in again** if you were logged out\n\nIf the issue persists, try uploading a different photo with better lighting 💡"
        ]
    },

    # ── Thanks / bye ──
    {
        'patterns': [r'\b(thank|thanks|thank you|cheers|appreciated|great|awesome|perfect|bye|goodbye|see you)\b'],
        'responses': [
            "You're very welcome! 😊 Happy styling! ✂️ Feel free to ask anytime you need help.",
            "Thanks for chatting! 🌟 May your hair always look perfect! Come back anytime 💇",
            "Cheers! 👋 Hope our recommendations give you a great new look! Come back anytime!"
        ]
    },

    # ── Who made this ──
    {
        'patterns': [r'\b(who made|who built|who created|developer|author|creator|thiruselvam|23cos263)\b'],
        'responses': [
            "👨‍💻 HairStyle AI was designed and built by **S.Thiruselvam** (Roll No: 23COS263) as an AI-powered personal styling assistant using Python, Flask, MediaPipe, and MongoDB."
        ]
    },

    # ── Help menu ──
    {
        'patterns': [r'\b(help|what can you do|what can you help|commands|options|menu)\b'],
        'responses': [
            "🤖 I'm your **HairStyle AI Assistant**! Here's what I can help you with:\n\n💇 **Hairstyles** – Ask about any hairstyle or recommendations\n🧔 **Beard Styles** – Ask about beard options for your face shape\n🎭 **Face Shapes** – Learn about different face shapes\n📸 **Photo Tips** – How to get the best analysis results\n🔐 **Account Help** – Login, register, history\n⚙️ **Technology** – How the AI works\n💰 **Pricing** – (It's free!)\n\nJust type your question naturally! 😊"
        ]
    },
]

# ── Fallback responses ──
FALLBACKS = [
    "🤔 Hmm, I'm not sure I understood that. I can help with **hairstyles, beard styles, face shapes, photo tips, and app usage**. Try asking something like *'What hairstyles suit a round face?'*",
    "💬 I'm specialized in hair & style questions! Try asking about:\n- Face shapes\n- Hairstyle recommendations\n- Beard styles\n- How to use the app",
    "🧐 I didn't quite catch that! I'm best at answering questions about **hairstyles, beard styles, and face shapes**. What would you like to know?"
]

import random

def get_bot_response(user_message: str) -> dict:
    """Match user message against knowledge base patterns and return a response."""
    msg = user_message.lower().strip()

    if not msg:
        return {'reply': "Please type a message so I can help you! 😊", 'type': 'info'}

    # Try each knowledge base entry
    for entry in KNOWLEDGE_BASE:
        for pattern in entry['patterns']:
            if re.search(pattern, msg, re.IGNORECASE):
                reply = random.choice(entry['responses'])
                return {'reply': reply, 'type': 'success'}

    # Fallback
    return {'reply': random.choice(FALLBACKS), 'type': 'fallback'}


@chatbot_bp.route('/api/chat', methods=['POST'])
def chat():
    """Chat API endpoint."""
    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'reply': "Please type a message! 😊", 'type': 'info'})

        result = get_bot_response(user_message)

        return jsonify({
            'reply': result['reply'],
            'type': result['type'],
            'timestamp': datetime.datetime.now().strftime('%I:%M %p')
        })

    except Exception as e:
        return jsonify({
            'reply': "Sorry, something went wrong on my end. Please try again! 🙏",
            'type': 'error'
        }), 500
