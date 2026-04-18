import os
from datetime import date, timedelta
from dotenv import load_dotenv
from fatsecret_client import FatSecretSyncClient
from sheets_client import SheetsClient
from garmin_client import GarminSyncClient
from weather_client import WeatherClient

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
    "Date", "Total Steps", "Distance (km)", "BMR Calories", "Active Calories", "Total Calories",
    "Floors Climbed", "Highly Active Seconds", "Active Seconds", "Sedentary Seconds", "Sleeping Seconds",
    "Moderate Intensity Minutes", "Vigorous Intensity Minutes", "Min HR", "Max HR", "Resting HR", "7 Day Avg Resting HR",
    "Min Average HR", "Max Average HR", "Body Battery Wake Time", "Body Battery Highest", "Body Battery Lowest",
    "Body Battery Charged Value", "Body Battery Drained Value", "Lowest SpO2", "Avg SpO2", "Highest Respiration", "Lowest Respiration",
    "Avg Respiration", "Average Stress Level", "Max Stress Level", "Stress Percentage", "Resting Stress Percentage", "Active Stress Percentage",
    "Weight (kg)", "Hydration (ml)", "Daily Average Hydration (ml)", "Sweat Loss (ml)", "Readiness Score", "Readiness Level", "Sleep Score",
    "Overnight HRV Avg", "HRV Status", "HRV Balanced Low", "HRV Balanced Upper", "Lactate Threshold HR", "Lactate Threshold Power",
    "VO2 Max", "Training Status", "Acute Load", "ACWR", "Load Focus", "Low Aerobic Load", "High Aerobic Load", "Anaerobic Load",
    "Total Sleep (hrs)", "Deep Sleep (hrs)", "Light Sleep (hrs)", "REM Sleep (hrs)", "Awake Time (hrs)", "Bedtime", "Wake Time", "Sleep Body Battery Recharge"
]

ACTIVITY_HEADERS = [
    "Activity ID", "Date", "Time", "Type", "Distance (km)", "Duration (HH:MM:SS)", "Pace (min/km)", "Calories",
    "Avg HR", "Max HR", "Aerobic TE", "Steps"
]

STRENGTH_HEADERS = [
    "Activity ID", "Date", "Start Time", "Set Number", "Exercise Category", "Exercise Name",
    "Reps", "Weight (kg)", "Set Duration (seconds)"
]

RUNNING_MASTER_HEADERS = [
    "Activity ID", "Activity Name", "Start Latitude", "Start Longitude", "Date", "Time", "Distance (km)", "Total Time", "Moving Time",
    "Average Pace (min/km)", "Grade Adjusted Pace (min/km)", "Max Pace (min/km)", "Walk Duration (HH:MM:SS)", "Walk Distance (m)", "Elevation Gain (m)", "Elevation Loss (m)",
    "Calories", "Estimated Sweat Loss (ml)", "Avg HR", "Max HR", "Z1 Mins", "Z2 Mins", "Z3 Mins", "Z4 Mins", "Z5 Mins",
    "Avg Stride Cadence (spm)", "Max Stride Cadence (spm)", "Avg Stride Length (cm)", "Avg Ground Contact Time (ms)",
    "Avg Vertical Oscillation (cm)", "Vertical Ratio (%)", "Avg Power (W)", "Max Power (W)", "Aerobic TE", "Anaerobic TE",
    "Training Effect Label", "Activity Training Load", "Body Battery Drain", "Workout RPE (1-10)", "Workout Feel (10-100)", "End Stamina (%)", "Normalized Power (W)",
    "Fastest Split 1km (min/km)", "Fastest Split 1 Mile (min/km)", "Fastest Split 5k (min/km)", "User Notes", "Temperature (°C)", "Humidity (%)", 
    "Dew Point (°C)", "Feels Like (°C)", "Precipitation (mm)", "Wind Speed (km/h)"
]

RUNNING_LAPWISE_HEADERS = [
    "Activity ID", "Date", "Time", "Lap Number", "Lap Distance (km)", "Lap Duration (MM:SS)",
    "Average Pace (min/km)", "Grade Adjusted Pace (min/km)", "Avg HR", "Max HR", "Avg Cadence (spm)",
    "Stride Length (cm)", "Ground Contact Time (ms)", "Vertical Oscillation (cm)", "Vertical Ratio (%)",
    "Average Power (Watts)", "Elevation Gain (m)", "Calories per lap"
]

LIFESTYLE_HEADERS = ["Date", "Behavior Name", "Status", "Category", "Details"]

def main():
    print("🚀 Starting Health-to-Sheets Sync...")
    load_dotenv(ENV_PATH)

    #target_date = date(2026, 2, 23)
    
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

    weather = WeatherClient()  # Using default coordinates for Bengaluru

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
        daily_row = garmin.get_everything_daily(target_iso, DAILY_HEADERS)
        # Note: If daily_row is a dict, ensure sheets_client is built to parse it, 
        # otherwise you may need to map values to the DAILY_HEADERS list.
        sheets.sync_to_tab("Daily_Master", daily_row, DAILY_HEADERS)
    except Exception as e:
        print(f"⚠️ Could not sync daily metrics: {e}")

    #2. Sync Garmin Activities & Deep Dives
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
            print(f"⛅ Fetching hyper-local weather for {len(running_master_rows)} runs...")
            
            for row in running_master_rows:
                run_date = row[4]  # Date
                run_time = row[5]  # Time
                run_lat  = row[2]  # Start Latitude
                run_lon  = row[3]  # Start Longitude
                
                # Pass coordinates directly to the API
                # Pass coordinates directly to the API
                temp, hum, dew, feels_like, precip, wind = weather.get_run_weather(run_date, run_time, run_lat, run_lon)
                
                # Append all 6 weather metrics to the row
                row.extend([temp, hum, dew, feels_like, precip, wind])
            sheets.sync_to_tab("Running_Master_Log", running_master_rows, RUNNING_MASTER_HEADERS, is_list=True)

        # Running Lapwise Log
        running_lapwise_rows = garmin.get_running_lapwise_log(target_iso)
        if running_lapwise_rows:
            print(f"🏁 Syncing {len(running_lapwise_rows)} total running laps...")
            sheets.sync_to_tab("Running_Lapwise_Log", running_lapwise_rows, RUNNING_LAPWISE_HEADERS, is_list=True)

    except Exception as e:
        print(f"⚠️ Could not sync activities: {e}")

    # 3. Sync Lifestyle/Behavioral data
    print(f"🧠 Fetching Behavioral Logs for {target_iso}...")
    try:
        lifestyle_rows = garmin.get_lifestyle_log(target_iso)
        if lifestyle_rows:
            print(f"📝 Syncing {len(lifestyle_rows)} lifestyle entries...")
            # 'is_list=True' because get_lifestyle_log returns a list of lists (rows)
            sheets.sync_to_tab("Lifestyle_Raw", lifestyle_rows, LIFESTYLE_HEADERS, is_list=True)
            sheets.process_lifestyle_logs(target_iso)
        else:
            print("ℹ️ No behavioral logs found for this date.")
    except Exception as e:
        print(f"⚠️ Could not sync lifestyle data: {e}")


    print("✅ Sync Complete!")

if __name__ == "__main__":
    main()