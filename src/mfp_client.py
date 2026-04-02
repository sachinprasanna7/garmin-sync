import myfitnesspal
from datetime import date

class MFPSyncClient:
    def __init__(self, username, cookiejar_path=None):
        # We use a cookiejar because of the Captcha restriction
        self.client = myfitnesspal.Client(username, cookiejar=cookiejar_path)

    def get_daily_nutrition(self, day_date):
        day = self.client.get_date(day_date.year, day_date.month, day_date.day)
        
        # 1. Get Totals
        totals = day.totals
        
        # 2. Get Itemized Food Log
        food_items = []
        for meal in day.meals:
            for entry in meal.entries:
                food_items.append([
                    day_date.isoformat(),
                    meal.name,
                    entry.name,
                    entry.totals.get('calories', 0),
                    entry.totals.get('protein', 0),
                    entry.totals.get('carbohydrates', 0),
                    entry.totals.get('fat', 0)
                ])
                
        return totals, food_items