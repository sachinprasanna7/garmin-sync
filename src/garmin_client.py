from datetime import date
from garminconnect import Garmin

class GarminSyncClient:
    def __init__(self, email, password):
        self.client = Garmin(email, password)
        self.client.login()

    def get_daily_metrics(self):
        today = date.today().isoformat()
        
        # Get various data points
        stats = self.client.get_user_summary(today)
        hydration = self.client.get_hydration_data(today)
        activities = self.client.get_activities(0, 1) # Latest activity

        # Return a clean dictionary of what we actually want
        return {
            "date": today,
            "steps": stats.get('totalSteps', 0),
            "resting_hr": stats.get('restingHeartRate', 0),
            "stress": stats.get('dailyStressLevel', 0),
            "hydration": hydration.get('dailyHydrationAmount', 0),
            "activity": activities[0]['activityName'] if activities else "Rest Day"
        }