import os
from datetime import date
from dotenv import load_dotenv
from fatsecret_client import FatSecretSyncClient
from sheets_client import SheetsClient
from garmin_client import GarminSyncClient

ENV_PATH = "secrets/.env"
SERVICE_ACCOUNT_PATH = "secrets/service_account.json"
SESSION_DIR = "secrets/garth_tokens"
FS_TOKEN_PATH = "secrets/fs_token.json"  

# --- FATSECRET HEADER DEFINITIONS ---
# Headers for the Detailed Itemized List
NUTRITION_ITEMIZED_HEADERS = [
    "Date", "Meal", "Food Name", "Servings", "Calories", "Protein (g)", 
    "Carbs (g)", "Fat (g)", "Saturated Fat (g)", "Polyunsaturated Fat (g)", 
    "Monounsaturated Fat (g)", "Cholesterol (mg)", "Sodium (mg)", "Potassium (mg)", 
    "Fiber (g)", "Sugar (g)", "Vitamin A (µg)", "Vitamin C (mg)", "Calcium (mg)", "Iron (mg)"
]

# Headers for the Daily Summary
NUTRITION_SUMMARY_HEADERS = [
    "Date", "Total Calories", "Total Protein (g)", "Total Carbs (g)", "Total Fat (g)", 
    "Total Saturated Fat (g)", "Total Polyunsaturated Fat (g)", "Total Monounsaturated Fat (g)",
    "Total Cholesterol (mg)", "Total Sodium (mg)", "Total Potassium (mg)", 
    "Total Fiber (g)", "Total Sugar (g)", "Total Vitamin A (µg)", "Total Vitamin C (mg)", "Total Calcium (mg)", "Total Iron (mg)"
]
# --------------------------

# --- GARMIN HEADER DEFINITIONS ---
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

def main():
    print("🚀 Starting Health-to-Sheets Sync (FatSecret Testing)...")
    load_dotenv(ENV_PATH)
    today_date = date.today()
    today_iso = today_date.isoformat()

    print("🔌 Initializing Clients...")
    
    #🛑 Garmin temporarily disabled due to 429 Rate Limit
    garmin = GarminSyncClient(
        os.getenv("GARMIN_EMAIL"),
        os.getenv("GARMIN_PASSWORD"),
        SESSION_DIR
    )

    fatsecret = FatSecretSyncClient(
        os.getenv("FATSECRET_KEY"),
        os.getenv("FATSECRET_SECRET"),
        FS_TOKEN_PATH
    )

    sheets = SheetsClient(
        SERVICE_ACCOUNT_PATH,
        os.getenv("SHEET_NAME")
    )

    # Sync FatSecret Nutrition Data
    print("🥗 Extracting FatSecret Nutrition Data...")
    try:
        daily_summary, itemized_log = fatsecret.get_daily_nutrition(today_date)

        if itemized_log:
            print(f"📝 Syncing {len(itemized_log)} food items to Nutrition_Daily (Itemized)...")
            sheets.sync_to_tab("Nutrition_Daily", itemized_log, NUTRITION_ITEMIZED_HEADERS, is_list=True)
        
        if daily_summary:
            print("🍽️ Syncing Daily Summary to Nutrition_Log...")
            sheets.sync_to_tab("Nutrition_Log", daily_summary, NUTRITION_SUMMARY_HEADERS)
            
    except Exception as e:
        print(f"⚠️ Could not sync nutrition data: {e}")

    # 1. Sync Garmin Daily Metrics
    print(f"📊 Fetching Master Daily Metrics for {today_iso}...")
    try:
        daily_row = garmin.get_everything_daily(today_iso)
        sheets.sync_to_tab("Daily_Master", daily_row, DAILY_HEADERS)
    except Exception as e:
        print(f"⚠️ Could not sync daily metrics: {e}")

    # 2. Sync Garmin Activities & Strength Data
    print("🏃 Extracting Activity Summaries and Set Data...")
    try:
        summary_rows, strength_rows = garmin.get_latest_activities(limit=5)
        
        if summary_rows:
            sheets.sync_to_tab("Activity_Summary", summary_rows, ACTIVITY_HEADERS, is_list=True)

        if strength_rows:
            print(f"🏋️ Found {len(strength_rows)} strength sets. Syncing...")
            sheets.sync_to_tab("Strength_Deep_Dive", strength_rows, STRENGTH_HEADERS, is_list=True)
    except Exception as e:
        print(f"⚠️ Could not sync activities: {e}")

    print("✅ Sync Complete!")

if __name__ == "__main__":
    main()