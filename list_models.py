"""List all Gemini models available to your API key that support image generation."""
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    from google import genai
except ImportError:
    print("Please install google-genai: pip install google-genai")
    exit(1)

client = genai.Client(api_key=API_KEY)

print("=" * 60)
print("ALL AVAILABLE MODELS:")
print("=" * 60)
image_models = []
for model in client.models.list():
    name = model.name
    methods = getattr(model, 'supported_actions', None) or getattr(model, 'supported_generation_methods', [])
    print(f"  {name}  |  methods: {methods}")
    # Flag potential image generation models
    if any(x in name.lower() for x in ['image', 'imagen', 'flash', 'vision']):
        image_models.append(name)

print()
print("=" * 60)
print("POTENTIAL IMAGE GENERATION MODELS:")
print("=" * 60)
for m in image_models:
    print(f"  {m}")
