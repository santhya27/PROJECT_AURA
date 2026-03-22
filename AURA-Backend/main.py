from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
from gtts import gTTS
import os
import time
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 1. Setup Static Folder for Audio
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. CORS Middleware (Crucial for React connection)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Supabase Config (Check your Key - it looks like a public key)
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(URL, KEY)

# 4. Updated Data Model (Matches your React handleAnalyze)
# 1. Update your Model to include budget
class UserData(BaseModel):
    user_id: str
    elec_units: float
    water_liters: float
    fuel_liters: float
    appliance_year: int = 2024
    language: str = "English"
    budget: str = "Standard" # Added this!

@app.post("/analyze")
async def analyze(data: UserData):
    try:
        print(f"--- Received Data from React: {data} ---")

        # 1. Language Mapping
        lang_map = {"Tamil": "ta", "Hindi": "hi", "English": "en"}
        lang_code = lang_map.get(data.language, "en")

        # 2. AGING LOGIC
        current_year = 2026
        age = current_year - data.appliance_year
        aging_factor = 1 + (max(0, age) * 0.02)
        real_units = data.elec_units * aging_factor

        # 3. TANGEDCO SLAB LOGIC (Updated to avoid 0)
        # Even under 100 units, let's apply a base rate of 1.50 for the demo
        if real_units <= 100: 
            cost = real_units * 1.50 
        elif real_units <= 400: 
            cost = real_units * 4.50
        elif real_units <= 500: 
            cost = real_units * 6.00
        else: 
            cost = real_units * 9.00

        # 4. CARBON FOOTPRINT
        carbon_kg = round((real_units * 0.82) + (data.fuel_liters * 2.31), 2)

        # 5. DYNAMIC ADVICE LOGIC (Based on Budget & Usage)
        # We create a dictionary that picks advice based on the 'budget' sent from React
        advice_options = {
            "en": {
                "Economy": "Pro-Tip: Switch to LED bulbs and clean your AC filters to save ₹300 monthly.",
                "Standard": f"Your {age}-year-old appliances are leaking energy. Upgrading could save 15% on bills.",
                "Premium": "Investment Tip: Your usage is perfect for a 3kW Solar Grid with a 4-year ROI."
            },
            "ta": {
                "Economy": "குறிப்பு: எல்இடி விளக்குகளுக்கு மாறுவதன் மூலம் மாதம் ₹300 வரை சேமிக்கலாம்.",
                "Standard": f"உங்கள் {age} வருட பழைய சாதனங்கள் அதிக மின்சாரத்தை பயன்படுத்துகின்றன.",
                "Premium": "முதலீடு: உங்கள் பயன்பாட்டிற்கு சோலார் பேனல்கள் சிறந்த லாபத்தை தரும்."
            },
            "hi": {
                "Economy": "टिप: एलईडी बल्ब का उपयोग करें और महीने में ₹300 बचाएं।",
                "Standard": f"आपके {age} साल पुराने उपकरण आपके बिल को बढ़ा रहे हैं।",
                "Premium": "निवेश टिप: आपके उपयोग के लिए सोलर ग्रिड सबसे अच्छा विकल्प है।"
            }
        }

        # Select the advice based on Language AND Budget
        lang_tips = advice_options.get(lang_code, advice_options["en"])
        final_advice = lang_tips.get(data.budget, lang_tips["Standard"])

        # 6. VOICE GENERATION
        tts = gTTS(text=final_advice, lang=lang_code)
        audio_filename = "advice.mp3"
        audio_path = os.path.join("static", audio_filename)
        tts.save(audio_path)

        return {
            "warning": "High Slab Alert!" if real_units > 400 else None,
            "carbon_footprint": carbon_kg,
            "bill_est": round(cost, 2),
            "real_units": round(real_units, 2),
            "advice": final_advice,
            "voice_url": f"/static/{audio_filename}?t={int(time.time())}"
        }

    except Exception as e:
        print(f"CRASH ERROR: {e}")
        return {"error": str(e)}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000) 