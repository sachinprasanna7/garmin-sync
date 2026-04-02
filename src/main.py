import os
from datetime import date
from dotenv import load_dotenv
# from garmin_client import GarminSyncClient
from fatsecret_client import FatSecretSyncClient
from sheets_client import SheetsClient

# Paths (Relative to /app in Docker)
ENV_PATH = "secrets/.env"
SERVICE_ACCOUNT_PATH = "secrets/service_account.json"
# SESSION_DIR = "secrets/garth_tokens"
FS_TOKEN_PATH = "secrets/fs_token.json"  

# --- HEADER DEFINITIONS ---
# ... (Garmin headers kept for tomorrow)
DAILY_HEADERS = [
    "Date", "Steps", "Distance (km)", "Active Calories", "Floors",
    "Resting HR", "Min HR", "Max HR", "Avg Stress", "Body Battery Max",
    "Body Battery Min", "Sleep Score", "Sleep Hours", "Hydration (Actual/Goal)",
    "Readiness Score", "Training Status", "VO2 Max", "Fitness Age",
    "Avg SpO2", "Avg Respiration", "Weight (kg)"
]

ACTIVITY_HEADERS = [
    "Activity ID", "Date/Time", "Name", "Type", "Distance (km)", "Duration",
    "Avg HR", "Max HR", "Calories", "Aerobic TE", "Anaerobic TE", "VO2 Max", "Steps"
]

STRENGTH_HEADERS = [
    "Activity ID", "Date", "Set #", "Exercise Name", "Reps", "Weight (kg)", "Category"
]

# --- NEW MASSIVE NUTRITION HEADERS ---
NUTRITION_DAILY_HEADERS = [
    "Date", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)", 
    "Cholesterol (mg)", "Sodium (mg)", "Fiber (g)", "Sugar (g)"
]

NUTRITION_LOG_HEADERS = [
    "Date", "Meal", "Food Name", "Servings", "Calories", "Protein (g)", 
    "Carbs (g)", "Fat (g)", "Saturated Fat (g)", "Polyunsaturated Fat (g)", 
    "Monounsaturated Fat (g)", "Cholesterol (mg)", "Sodium (mg)", "Potassium (mg)", 
    "Fiber (g)", "Sugar (g)", "Vitamin A", "Vitamin C", "Calcium", "Iron"
]
# --------------------------

def main():
    print("🚀 Starting Health-to-Sheets Sync (Nutrition Only Mode)...")
    load_dotenv(ENV_PATH)
    
    today_date = date.today()
    # today_iso = today_date.isoformat()

    print("🔌 Initializing Clients...")
    
    # 🛑 Garmin temporarily disabled due to 429 Rate Limit
    # garmin = GarminSyncClient(
    #     os.getenv("GARMIN_EMAIL"),
    #     os.getenv("GARMIN_PASSWORD"),
    #     SESSION_DIR
    # )

    fatsecret = FatSecretSyncClient(
        os.getenv("FATSECRET_KEY"),
        os.getenv("FATSECRET_SECRET"),
        FS_TOKEN_PATH
    )

    sheets = SheetsClient(
        SERVICE_ACCOUNT_PATH,
        os.getenv("SHEET_NAME")
    )

    # --- GARMIN SYNC BLOCKS DISABLED ---
    # print(f"📊 Fetching Master Daily Metrics for {today_iso}...")
    # ...
    # print("🏃 Extracting Activity Summaries and Set Data...")
    # ...

    # 3. Sync FatSecret Nutrition Data
    print("🥗 Extracting FatSecret Nutrition Data...")
    try:
        daily_macros, food_log = fatsecret.get_daily_nutrition(today_date)

        if daily_macros:
            print("🍽️ Syncing Daily Macros...")
            sheets.sync_to_tab("Nutrition_Daily", daily_macros, NUTRITION_DAILY_HEADERS)
        
        if food_log:
            print(f"📝 Syncing {len(food_log)} individual food items with full micronutrients...")
            sheets.sync_to_tab("Nutrition_Log", food_log, NUTRITION_LOG_HEADERS, is_list=True)
    except Exception as e:
        print(f"⚠️ Could not sync nutrition data: {e}")

    print("✅ Full Sync Complete!")

if __name__ == "__main__":
    main()