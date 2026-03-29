import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

def test_gemini_text():
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Hello, this is a test. Reply with 'OK'."
        )
        print("Text Generate OK:", response.text.strip())
    except Exception as e:
        print("Text Generate Error:", e)

if __name__ == "__main__":
    test_gemini_text()
