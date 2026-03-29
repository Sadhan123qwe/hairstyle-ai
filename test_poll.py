
import requests, io, random, time
from PIL import Image

def test_pollinations():
    prompt = "A man with a quiff hairstyle"
    for i in range(3):
        seed = int(time.time() * 1000) + random.randint(1, 1000)
        url = f"https://image.pollinations.ai/prompt/{prompt}?width=512&height=512&nologo=true&seed={seed}"
        print(f"Requesting: {url}")
        r = requests.get(url)
        if r.status_code == 200:
            img = Image.open(io.BytesIO(r.content))
            img.save(f"/tmp/test_poll_{i}.jpg")
            print(f"Saved test_poll_{i}.jpg")
        time.sleep(1)

if __name__ == "__main__":
    test_pollinations()
