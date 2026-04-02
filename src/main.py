import os
from datetime import date
from dotenv import load_dotenv
from fatsecret_client import FatSecretSyncClient
from sheets_client import SheetsClient

ENV_PATH = "secrets/.env"
SERVICE_ACCOUNT_PATH = "secrets/service_account.json"
FS_TOKEN_PATH = "secrets/fs_token.json"  

# --- UPDATED HEADER DEFINITIONS ---
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

def main():
    print("🚀 Starting Health-to-Sheets Sync (FatSecret Testing)...")
    load_dotenv(ENV_PATH)
    today_date = date.today()

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

    print("✅ Sync Complete!")

if __name__ == "__main__":
    main()