import os
from dotenv import load_dotenv
from garmin_client import GarminSyncClient
from sheets_client import SheetsClient

# Note: In Docker, paths are relative to /app
ENV_PATH = "secrets/.env"
SERVICE_ACCOUNT_PATH = "secrets/service_account.json"

def main():
    # 1. Load config
    load_dotenv(ENV_PATH)
    
    # 2. Fetch from Garmin
    print("🚀 Fetching data from Garmin...")
    garmin = GarminSyncClient(
        os.getenv("GARMIN_EMAIL"), 
        os.getenv("GARMIN_PASSWORD")
    )
    daily_data = garmin.get_daily_metrics()

    # 3. Push to Sheets
    print(f"📊 Syncing metrics for {daily_data['date']}...")
    sheets = SheetsClient(
        SERVICE_ACCOUNT_PATH, 
        os.getenv("SHEET_NAME")
    )
    sheets.append_daily_row(daily_data)

    print("✅ Sync Complete!")

if __name__ == "__main__":
    main()