import os
import io
import sys
from PIL import Image
from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Please install google-genai: pip install google-genai")
    sys.exit(1)

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

def test_gemini_image():
    if not API_KEY:
        print("Error: GEMINI_API_KEY not found in .env")
        return

    print("Initializing Gemini Client...")
    client = genai.Client(api_key=API_KEY)
    
    prompt = "A professional studio portrait of a man with a classic pompadour hairstyle, warm cinematic lighting."
    print(f"Requesting image from Gemini API (Imagen 3)...")
    
    try:
        # Generate image using Imagen 3
        result = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="1:1"
            )
        )
        
        for i, generated_image in enumerate(result.generated_images):
            image = Image.open(io.BytesIO(generated_image.image.image_bytes))
            filename = f"gemini_sdk_test_{i}.jpg"
            image.save(filename)
            print(f"Success! Saved as {filename}")

    except Exception as e:
        print(f"Exception occurred with imagen-3.0-generate-002: {e}")
        print("Trying fallback model name 'imagen-3.0-generate-001'...")
        try:
             result = client.models.generate_images(
                 model='imagen-3.0-generate-001',
                 prompt=prompt,
                 config=types.GenerateImagesConfig(
                     number_of_images=1,
                     output_mime_type="image/jpeg",
                     aspect_ratio="1:1"
                 )
             )
             for i, generated_image in enumerate(result.generated_images):
                 image = Image.open(io.BytesIO(generated_image.image.image_bytes))
                 filename = f"gemini_sdk_test_fallback_{i}.jpg"
                 image.save(filename)
                 print(f"Success (Fallback)! Saved as {filename}")
        except Exception as e2:
             print(f"Fallback Exception occurred: {e2}")

if __name__ == "__main__":
    test_gemini_image()
