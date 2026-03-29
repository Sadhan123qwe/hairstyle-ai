"""Test Gemini API - list models and try image generation."""
import os, sys, io
from dotenv import load_dotenv

load_dotenv()
API_KEY = "AIzaSyDOi5k_rX-abKk8SW8GCbYu3-4OarcFVgQ"

print(f"Python: {sys.version}")
print(f"API key: {API_KEY[:20]}...")

try:
    import google.genai as genai
    print(f"google-genai imported OK")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

client = genai.Client(api_key=API_KEY)

# List all models
print("\n=== Available Models ===")
try:
    models = list(client.models.list())
    for m in models:
        print(f"  {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")

# Try image generation with gemini-2.0-flash-exp (standard model)
print("\n=== Testing Image Generation ===")
MODELS_TO_TRY = [
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash-exp-image-generation",
]

for model_name in MODELS_TO_TRY:
    print(f"\nTrying: {model_name}")
    try:
        from google.genai import types
        response = client.models.generate_content(
            model=model_name,
            contents="Generate an image of a man with a pompadour hairstyle, studio portrait.",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                print(f"  SUCCESS! Got image ({len(part.inline_data.data)} bytes)")
                from PIL import Image
                img = Image.open(io.BytesIO(part.inline_data.data))
                img.save(f"test_output_{model_name.replace('/', '_')}.jpg")
                print(f"  Saved as test_output_{model_name.replace('/', '_')}.jpg")
                break
        else:
            print(f"  No image in response. Text: {response.text[:200] if hasattr(response, 'text') else 'N/A'}")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\nDone.")
