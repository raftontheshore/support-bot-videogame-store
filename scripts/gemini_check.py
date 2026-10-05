import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Models with 'flash' in the name:")
for model in client.models.list():
    if "flash" in model.name:
        print(" ", model.name)

model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
print(f"\nTrying {model_name} ...")
response = client.models.generate_content(model=model_name, contents="Say hi in 3 words.")
print(response.text)