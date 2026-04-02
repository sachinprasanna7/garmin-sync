import os
from datetime import date
from dotenv import load_dotenv
from garmin_client import GarminSyncClient
from sheets_client import SheetsClient

# Paths (Relative to /app in Docker)
ENV_PATH = "secrets/.env"
SERVICE_ACCOUNT_PATH = "secrets/service_account.json"
SESSION_PATH = "secrets/session.json"

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
# --------------------------

def main():
    print("🚀 Starting Garmin-to-Sheets Sync...")
    load_dotenv(ENV_PATH)
    today = date.today().isoformat()
    
    garmin = GarminSyncClient(
        os.getenv("GARMIN_EMAIL"), 
        os.getenv("GARMIN_PASSWORD"),
        SESSION_PATH
    )
    
    sheets = SheetsClient(
        SERVICE_ACCOUNT_PATH, 
        os.getenv("SHEET_NAME")
    )

    # 1. Sync Daily Metrics
    print(f"📊 Fetching Master Daily Metrics for {today}...")
    try:
        daily_row = garmin.get_everything_daily(today)
        sheets.sync_to_tab("Daily_Master", daily_row, DAILY_HEADERS)
    except Exception as e:
        print(f"⚠️ Could not sync daily metrics: {e}")

    # 2. Sync Activities & Strength Data
    print("🏃 Extracting Activity Summaries and Set Data...")
    try:
        summary_rows, strength_rows = garmin.get_latest_activities(limit=5)
        
        # Sync General Activities
        sheets.sync_to_tab("Activity_Summary", summary_rows, ACTIVITY_HEADERS, is_list=True)
        
        # Sync Strength Deep Dive (if any exist in the last 5 activities)
        if strength_rows:
            print(f"🏋️ Found {len(strength_rows)} strength sets. Syncing...")
            sheets.sync_to_tab("Strength_Deep_Dive", strength_rows, STRENGTH_HEADERS, is_list=True)
            
    except Exception as e:
        print(f"⚠️ Could not sync activities: {e}")

    print("✅ Sync Complete!")

if __name__ == "__main__":
    main()