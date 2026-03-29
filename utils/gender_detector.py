"""
Gender Detection Utility — v4

Detection strategy (in priority order):
  1. OpenCV DNN + pre-trained Caffe gender model (local, no API, no quota)
     Model: GilLevi/AgeGenderDeepLearning — auto-downloaded on first run
  2. Gemini 2.0 Flash Lite — cloud API (only if local model fails/unavailable)

The Caffe model runs entirely on CPU with OpenCV (already a project dependency).
No extra packages needed. Models are ~30 MB and cached in utils/models/.
"""

import os
import base64
import json
import urllib.request
import urllib.error
import urllib.parse

import cv2
import numpy as np

# ── Model paths ────────────────────────────────────────────────────────────────
_UTILS_DIR   = os.path.dirname(os.path.abspath(__file__))
_MODELS_DIR  = os.path.join(_UTILS_DIR, "gender_models")

_PROTO_PATH  = os.path.join(_MODELS_DIR, "deploy_gender.prototxt")
_MODEL_PATH  = os.path.join(_MODELS_DIR, "gender_net.caffemodel")

# Hosted files (GitHub raw / direct links)
_PROTO_URL = (
    "https://raw.githubusercontent.com/spmallick/learnopencv/"
    "master/AgeGender/gender_deploy.prototxt"
)
_MODEL_URL = (
    "https://github.com/smahesh29/Gender-and-Age-Detection/"
    "raw/master/gender_net.caffemodel"
)

GENDER_LIST = ["Male", "Female"]
MODEL_MEAN  = (78.4263377603, 87.7689143739, 114.895847746)  # BGR mean for VGG face


# ─────────────────────────────────────────────────────────────────────────────
#  Helper — download model files once
# ─────────────────────────────────────────────────────────────────────────────
def _ensure_models() -> bool:
    """Download model files if missing. Returns True on success."""
    os.makedirs(_MODELS_DIR, exist_ok=True)

    for path, url in [(_PROTO_PATH, _PROTO_URL), (_MODEL_PATH, _MODEL_URL)]:
        if not os.path.exists(path):
            print(f"[GenderDetect] Downloading {os.path.basename(path)} …")
            try:
                urllib.request.urlretrieve(url, path)
                print(f"[GenderDetect] Downloaded → {path}")
            except Exception as e:
                print(f"[GenderDetect] Download failed for {url}: {e}")
                return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  STRATEGY 1 — OpenCV DNN Caffe gender model (local, no API)
# ─────────────────────────────────────────────────────────────────────────────
def _detect_with_opencv(image_path: str) -> str:
    """
    Detect gender using a pre-trained Caffe model via OpenCV DNN.
    Returns 'male' or 'female'. Raises RuntimeError on failure.
    """
    if not _ensure_models():
        raise RuntimeError("Could not download gender model files")

    # Load model (cached by OS after first call)
    net = cv2.dnn.readNet(_MODEL_PATH, _PROTO_PATH)

    # Read image
    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError(f"cv2.imread failed for {image_path}")

    # Use the full image as the face crop (mediapipe already confirmed a face exists)
    # Optionally detect face first for better accuracy
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                           minSize=(60, 60))

    if len(faces) > 0:
        # Use the largest detected face
        x, y, w, h = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
        pad = int(0.1 * max(w, h))
        x1 = max(0, x - pad);  y1 = max(0, y - pad)
        x2 = min(img.shape[1], x + w + pad)
        y2 = min(img.shape[0], y + h + pad)
        face_img = img[y1:y2, x1:x2]
    else:
        # No face detected — use centre crop of full image
        print("[GenderDetect][OpenCV] No face cascade hit — using full image")
        face_img = img

    blob = cv2.dnn.blobFromImage(
        face_img, 1.0, (227, 227), MODEL_MEAN, swapRB=False
    )
    net.setInput(blob)
    preds = net.forward()  # shape: (1, 2)

    male_conf   = float(preds[0][0])
    female_conf = float(preds[0][1])

    print(
        f"[GenderDetect][OpenCV] Male={male_conf:.3f}  Female={female_conf:.3f}"
    )

    return "female" if female_conf > male_conf else "male"


# ─────────────────────────────────────────────────────────────────────────────
#  STRATEGY 2 — Gemini Flash Lite (cloud fallback)
# ─────────────────────────────────────────────────────────────────────────────
GENDER_PROMPT = """You are an expert vision AI specialising in facial gender classification.

Look at the face in the image and classify the person's gender.

Feminine cues: makeup, longer styled hair, soft/round jaw, arched brows, fuller lips.
Masculine cues: beard/stubble, square jaw, heavy brow ridge, shorter hair, wider neck.

Output EXACTLY one word — no punctuation, no explanation:
  female
OR
  male"""

GEMINI_MODEL = "gemini-2.0-flash-lite"
GEMINI_URL   = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={{key}}"
)


def _detect_with_gemini(image_path: str, api_key: str) -> str:
    """Cloud fallback using Gemini Flash Lite."""
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(image_path)[1].lower()
    mime_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")

    payload = {
        "contents": [{"parts": [
            {"text": GENDER_PROMPT},
            {"inline_data": {"mime_type": mime_type, "data": image_b64}},
        ]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 20},
    }
    url  = GEMINI_URL.format(key=api_key)
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini HTTP {e.code}: {body[:200]}")

    result = json.loads(raw)
    candidates = result.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"No candidates: {result.get('promptFeedback')}")

    text = (
        candidates[0].get("content", {}).get("parts", [{}])[0]
        .get("text", "").strip().lower()
    )
    print(f"[GenderDetect][Gemini] raw={text!r}")

    if "female" in text:
        return "female"
    if "male" in text:
        return "male"
    raise RuntimeError(f"Unrecognised Gemini token: {text!r}")


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────
def detect_gender(image_path: str) -> str:
    """
    Detect gender from a face image.

    Tries local OpenCV Caffe model first, then Gemini Flash Lite as fallback.

    Returns 'male' or 'female'.
    Raises RuntimeError if both strategies fail.
    """
    # ── Strategy 1: OpenCV local model ────────────────────────────────────────
    try:
        gender = _detect_with_opencv(image_path)
        print(f"[GenderDetect] ✓ OpenCV → {gender}")
        return gender
    except Exception as e:
        print(f"[GenderDetect] OpenCV failed ({e}), trying Gemini fallback…")

    # ── Strategy 2: Gemini Flash Lite ─────────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key:
        try:
            gender = _detect_with_gemini(image_path, api_key)
            print(f"[GenderDetect] ✓ Gemini → {gender}")
            return gender
        except Exception as e:
            print(f"[GenderDetect] Gemini fallback failed ({e})")
    else:
        print("[GenderDetect] GEMINI_API_KEY not set — skipping cloud fallback")

    raise RuntimeError("All gender detection strategies failed")
