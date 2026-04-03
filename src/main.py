import os
from datetime import date, timedelta
from dotenv import load_dotenv
from fatsecret_client import FatSecretSyncClient
from sheets_client import SheetsClient
from garmin_client import GarminSyncClient

ENV_PATH = "secrets/.env"
SERVICE_ACCOUNT_PATH = "secrets/service_account.json"
SESSION_DIR = "secrets" # Updated to point directly to the secrets folder
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
    "Activity ID", "Date", "Time", "Type", "Distance (km)", "Duration",
    "Pace (min/km)", "Calories", "Avg HR", "Max HR", "Aerobic TE", "Steps"
]

STRENGTH_HEADERS = [
    "Activity ID", "Date", "Time", "Set #", "Category", "Exercise Name", "Reps", "Weight (kg)", "Duration (s)"
]

RUNNING_MASTER_HEADERS = [
    "Activity ID", "Name", "Date", "Time", "Distance (km)", "Total Time", "Moving Time",
    "Avg Pace (min/km)", "Grade Adjusted Pace", "Max Pace", "Elevation Gain (m)", "Elevation Loss (m)",
    "Total Calories", "Estimated Sweat Loss (ml)", "Avg HR", "Max HR", "Z1 Mins", "Z2 Mins",
    "Z3 Mins", "Z4 Mins", "Z5 Mins", "Avg Cadence (spm)", "Max Cadence", "Stride Length (cm)",
    "Ground Contact Time (ms)", "Vertical Oscillation (cm)", "Vertical Ratio (%)", "Avg Power (W)",
    "Max Power (W)", "Aerobic TE", "Anaerobic TE", "TE Label", "Training Load", "Body Battery Drain",
    "Fastest 1km", "Fastest 1 Mile", "Fastest 5k"
]

RUNNING_LAPWISE_HEADERS = [
    "Activity ID", "Date", "Time", "Lap Number", "Lap Distance (km)", "Lap Duration (MM:SS)",
    "Average Pace (min/km)", "Grade Adjusted Pace (min/km)", "Avg HR", "Max HR", "Avg Cadence (spm)",
    "Stride Length (cm)", "Ground Contact Time (ms)", "Vertical Oscillation (cm)", "Vertical Ratio (%)",
    "Running Power (Watts)", "Elevation Gain (m)", "Calories per lap"
]

def main():
    print("🚀 Starting Health-to-Sheets Sync...")
    load_dotenv(ENV_PATH)
    
    # Set the target date to YESTERDAY to ensure complete data sync
    target_date = date.today() - timedelta(days=1)
    target_iso = target_date.isoformat()

    print(f"📅 Target Sync Date: {target_iso}")
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

    # Sync FatSecret Nutrition Data
    print("🥗 Extracting FatSecret Nutrition Data...")
    try:
        # Passed target_date to keep FS aligned with Garmin's yesterday sync
        daily_summary, itemized_log = fatsecret.get_daily_nutrition(target_date)

        if itemized_log:
            print(f"📝 Syncing {len(itemized_log)} food items to Nutrition_Daily (Itemized)...")
            sheets.sync_to_tab("Nutrition_Daily", itemized_log, NUTRITION_ITEMIZED_HEADERS, is_list=True)
        
        if daily_summary:
            print("🍽️ Syncing Daily Summary to Nutrition_Log...")
            sheets.sync_to_tab("Nutrition_Log", daily_summary, NUTRITION_SUMMARY_HEADERS)
            
    except Exception as e:
        print(f"⚠️ Could not sync nutrition data: {e}")

    # 1. Sync Garmin Daily Metrics
    print(f"📊 Fetching Master Daily Metrics for {target_iso}...")
    try:
        daily_row = garmin.get_everything_daily(target_iso)
        # Note: If daily_row is a dict, ensure sheets_client is built to parse it, 
        # otherwise you may need to map values to the DAILY_HEADERS list.
        sheets.sync_to_tab("Daily_Master", daily_row, DAILY_HEADERS)
    except Exception as e:
        print(f"⚠️ Could not sync daily metrics: {e}")

    # 2. Sync Garmin Activities & Deep Dives
    print("🏃 Extracting Activity Summaries and Deep Dives...")
    try:
        # General Activity Log
        activity_rows = garmin.get_activity_log(target_iso)
        if activity_rows:
            print(f"📝 Syncing {len(activity_rows)} general activities...")
            sheets.sync_to_tab("Activity_Log", activity_rows, ACTIVITY_HEADERS, is_list=True)

        # Strength Deep Dive
        strength_rows = garmin.get_strength_log(target_iso)
        if strength_rows:
            print(f"🏋️ Found {len(strength_rows)} strength sets. Syncing...")
            sheets.sync_to_tab("Strength_Log", strength_rows, STRENGTH_HEADERS, is_list=True)
            
        # Running Master Log
        running_master_rows = garmin.get_running_master_log(target_iso)
        if running_master_rows:
            print(f"⏱️ Syncing {len(running_master_rows)} running master logs...")
            sheets.sync_to_tab("Running_Master_Log", running_master_rows, RUNNING_MASTER_HEADERS, is_list=True)

        # Running Lapwise Log
        running_lapwise_rows = garmin.get_running_lapwise_log(target_iso)
        if running_lapwise_rows:
            print(f"🏁 Syncing {len(running_lapwise_rows)} total running laps...")
            sheets.sync_to_tab("Running_Lapwise_Log", running_lapwise_rows, RUNNING_LAPWISE_HEADERS, is_list=True)

    except Exception as e:
        print(f"⚠️ Could not sync activities: {e}")

    print("✅ Sync Complete!")

if __name__ == "__main__":
    main()