import json
from datetime import date, datetime  # <-- Added datetime here
from fatsecret import Fatsecret

class FatSecretSyncClient:
    def __init__(self, consumer_key, consumer_secret, token_path):
        with open(token_path, "r") as f:
            session_token = tuple(json.load(f))
        self.fs = Fatsecret(consumer_key, consumer_secret, session_token=session_token)

    def get_daily_nutrition(self, target_date: date):
        iso_date = target_date.isoformat()

        # THE FIX: Convert the standard `date` object into a `datetime` object at Midnight.
        # This is strictly what the fatsecret python wrapper requires to not crash.
        target_datetime = datetime.combine(target_date, datetime.min.time())

        # 1. Fetch Itemized Log (The detailed list)
        food_log_rows = []
        total_calories = 0
        total_protein = 0
        total_carbohydrate = 0
        total_fat = 0
        total_saturated_fat = 0
        total_polyunsaturated_fat = 0
        total_monounsaturated_fat = 0
        total_cholesterol = 0
        total_sodium = 0
        total_potassium = 0
        total_fiber = 0
        total_sugar = 0
        total_vitamin_a = 0
        total_vitamin_c = 0
        total_calcium = 0
        total_iron = 0

        try:
            # Pass the datetime object we just created
            entries_response = self.fs.food_entries_get(date=target_datetime)
            
            if not entries_response:
                entries = []
            elif isinstance(entries_response, dict):
                entries = [entries_response]
            else:
                entries = entries_response
                
            for entry in entries:
                # Summing up for our summary row
                total_calories += float(entry.get('calories', 0))
                total_protein += float(entry.get('protein', 0))
                total_carbohydrate += float(entry.get('carbohydrate', 0))
                total_fat += float(entry.get('fat', 0))
                total_saturated_fat += float(entry.get('saturated_fat', 0))
                total_polyunsaturated_fat += float(entry.get('polyunsaturated_fat', 0))
                total_monounsaturated_fat += float(entry.get('monounsaturated_fat', 0))
                total_cholesterol += float(entry.get('cholesterol', 0))
                total_sodium += float(entry.get('sodium', 0))
                total_potassium += float(entry.get('potassium', 0))
                total_fiber += float(entry.get('fiber', 0))
                total_sugar += float(entry.get('sugar', 0))
                total_vitamin_a += float(entry.get('vitamin_a', 0))
                total_vitamin_c += float(entry.get('vitamin_c', 0))
                total_calcium += float(entry.get('calcium', 0))
                total_iron += float(entry.get('iron', 0))

                # Itemized log data (Order matches your JSON requirement)
                food_log_rows.append([
                    iso_date,
                    entry.get('meal', 'Unknown'),
                    entry.get('food_entry_name', 'Unknown Food'),
                    entry.get('number_of_units', '1'),
                    entry.get('calories', '0'),
                    entry.get('protein', '0'),
                    entry.get('carbohydrate', '0'),
                    entry.get('fat', '0'),
                    entry.get('saturated_fat', '0'),
                    entry.get('polyunsaturated_fat', '0'),
                    entry.get('monounsaturated_fat', '0'),
                    entry.get('cholesterol', '0'),
                    entry.get('sodium', '0'),
                    entry.get('potassium', '0'),
                    entry.get('fiber', '0'),
                    entry.get('sugar', '0'),
                    entry.get('vitamin_a', '0'),
                    entry.get('vitamin_c', '0'),
                    entry.get('calcium', '0'),
                    entry.get('iron', '0')
                ])
        except Exception as e:
            print(f"⚠️ Could not fetch food log: {e}")

        if not food_log_rows:
            return None, []

        # 2. Build the Daily Summary Row
        daily_summary_row = [
            iso_date,
            str(round(total_calories, 2)),
            str(round(total_protein, 2)),
            str(round(total_carbohydrate, 2)),
            str(round(total_fat, 2)),
            str(round(total_saturated_fat, 2)),
            str(round(total_polyunsaturated_fat, 2)),
            str(round(total_monounsaturated_fat, 2)),
            str(round(total_cholesterol, 2)),
            str(round(total_sodium, 2)),
            str(round(total_potassium, 2)),
            str(round(total_fiber, 2)),
            str(round(total_sugar, 2)),
            str(round(total_vitamin_a, 2)),
            str(round(total_vitamin_c, 2)),
            str(round(total_calcium, 2)),
            str(round(total_iron, 2))
        ]

        return daily_summary_row, food_log_rows