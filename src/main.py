import os
from datetime import date
from dotenv import load_dotenv
from garmin_client import GarminSyncClient
from fatsecret_client import FatSecretSyncClient  # <-- New Import
from sheets_client import SheetsClient

# Paths (Relative to /app in Docker)
ENV_PATH = "secrets/.env"
SERVICE_ACCOUNT_PATH = "secrets/service_account.json"
SESSION_DIR = "secrets/garth_tokens"
FS_TOKEN_PATH = "secrets/fs_token.json"  # <-- FatSecret Token Path

# --- HEADER DEFINITIONS ---
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

NUTRITION_DAILY_HEADERS = [
    "Date", "Calories", "Protein", "Carbs", "Fat"
]

NUTRITION_LOG_HEADERS = [
    "Date", "Meal", "Food", "Calories", "Protein", "Carbs", "Fat"
]
# --------------------------

def main():
    print("🚀 Starting Health-to-Sheets Sync...")
    load_dotenv(ENV_PATH)
    
    # We keep a date object for FatSecret and an ISO string for Garmin
    today_date = date.today()
    today_iso = today_date.isoformat()

    print("🔌 Initializing Clients...")
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
        sheets.sync_to_tab("Activity_Summary", summary_rows, ACTIVITY_HEADERS, is_list=True)

        if strength_rows:
            print(f"🏋️ Found {len(strength_rows)} strength sets. Syncing...")
            sheets.sync_to_tab("Strength_Deep_Dive", strength_rows, STRENGTH_HEADERS, is_list=True)
    except Exception as e:
        print(f"⚠️ Could not sync activities: {e}")

    # 3. Sync FatSecret Nutrition Data
    print("🥗 Extracting FatSecret Nutrition Data...")
    try:
        daily_macros, food_log = fatsecret.get_daily_nutrition(today_date)

        if daily_macros:
            print("🍽️ Syncing Daily Macros...")
            sheets.sync_to_tab("Nutrition_Daily", daily_macros, NUTRITION_DAILY_HEADERS)
        
        if food_log:
            print(f"📝 Syncing {len(food_log)} individual food items...")
            sheets.sync_to_tab("Nutrition_Log", food_log, NUTRITION_LOG_HEADERS, is_list=True)
    except Exception as e:
        print(f"⚠️ Could not sync nutrition data: {e}")

    print("✅ Full Sync Complete!")

if __name__ == "__main__":
    main()