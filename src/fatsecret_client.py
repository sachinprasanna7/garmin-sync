import os
import json
from datetime import date
from fatsecret import Fatsecret

class FatSecretSyncClient:
    def __init__(self, consumer_key, consumer_secret, token_path):
        # 1. Load the tokens we generated in the setup script
        with open(token_path, "r") as f:
            session_token = tuple(json.load(f)) # Library expects a tuple
            
        # 2. Initialize the client fully authenticated
        self.fs = Fatsecret(consumer_key, consumer_secret, session_token=session_token)

    def get_daily_nutrition(self, target_date: date):
        """Fetches both the daily macro summary and the itemized food log."""
        
        # FatSecret API uses "days since Jan 1, 1970"
        epoch_date = (target_date - date(1970, 1, 1)).days
        iso_date = target_date.isoformat()

        # 1. Fetch Daily Snapshot (Totals)
        try:
            # We fetch the month and filter for our specific day
            month_data = self.fs.food_entries_get_month(date=epoch_date)
            # Find the specific day in the list
            day_summary = next((d for d in month_data if str(d['date_int']) == str(epoch_date)), None)
        except Exception:
            day_summary = None

        if not day_summary:
            print(f"⚠️ No food logged in FatSecret for {iso_date}")
            return None, []

        daily_row = [
            iso_date,
            day_summary.get('calories', 0),
            day_summary.get('protein', 0),
            day_summary.get('carbohydrate', 0),
            day_summary.get('fat', 0)
        ]

        # 2. Fetch Meal-by-Meal Log
        food_log_rows = []
        try:
            # Gets every single entry logged that day
            entries = self.fs.food_entries_get(date=epoch_date)
            
            # The API returns a dict if there's only 1 item, or a list if multiple. Let's normalize it.
            if isinstance(entries, dict):
                entries = [entries]
                
            for entry in entries:
                food_log_rows.append([
                    iso_date,
                    entry.get('meal', 'Unknown'), # Breakfast, Lunch, Dinner
                    entry.get('food_entry_name', 'Unknown Food'),
                    entry.get('calories', 0),
                    entry.get('protein', 0),
                    entry.get('carbohydrate', 0),
                    entry.get('fat', 0)
                ])
        except Exception as e:
            print(f"⚠️ Could not fetch detailed food log: {e}")

        return daily_row, food_log_rows