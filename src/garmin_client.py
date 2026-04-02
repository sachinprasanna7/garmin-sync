import json
import os
import datetime
from garminconnect import Garmin

class GarminSyncClient:
    def __init__(self, email, password, session_path):
        self.session_path = session_path
        self.client = None

        if os.path.exists(self.session_path):
            with open(self.session_path, "r") as f:
                saved_session = json.load(f)
                self.client = Garmin(session_data=saved_session)
                self.client.login()
        
        if not self.client:
            self.client = Garmin(email, password)
            self.client.login()
            with open(self.session_path, "w") as f:
                json.dump(self.client.session_data, f)

    def get_everything_daily(self, day):
        """Fetches a massive array of daily metrics."""
        # Fetch from multiple endpoints
        stats = self.client.get_stats_and_body(day)
        readiness = self.client.get_training_readiness(day)
        status = self.client.get_training_status(day)
        sleep = self.client.get_sleep_data(day)
        hydration = self.client.get_hydration_data(day)
        rhr = self.client.get_rhr_day(day)
        spo2 = self.client.get_spo2_data(day)
        resp = self.client.get_respiration_data(day)
        max_met = self.client.get_max_metrics(day)

        # Flatten into a single row
        return [
            day,
            stats.get('totalSteps', 0),
            stats.get('totalDistanceMeters', 0) / 1000,
            stats.get('activeKilocalories', 0),
            stats.get('floorsClimbed', 0),
            rhr.get('allMetrics', {}).get('metricsMap', {}).get('WELLNESS_RESTING_HEART_RATE', [{}])[0].get('value', 'N/A') if isinstance(rhr, dict) else 'N/A',
            stats.get('minHeartRate', 'N/A'),
            stats.get('maxHeartRate', 'N/A'),
            stats.get('averageStressLevel', 'N/A'),
            stats.get('bodyBatteryHighestValue', 'N/A'),
            stats.get('bodyBatteryLowestValue', 'N/A'),
            sleep.get('dailySleepDTO', {}).get('sleepScore', 'N/A') if isinstance(sleep, dict) else 'N/A',
            (sleep.get('dailySleepDTO', {}).get('sleepTimeSeconds', 0) / 3600) if isinstance(sleep, dict) else 'N/A',
            f"{hydration.get('dailyHydrationAmount', 0)}/{hydration.get('dailyHydrationGoal', 0)}" if isinstance(hydration, dict) else 'N/A',
            readiness[0].get('score', 'N/A') if isinstance(readiness, list) and readiness else 'N/A',
            status.get('trainingStatus', 'N/A') if isinstance(status, dict) else 'N/A',
            max_met[0].get('vo2Max', 'N/A') if isinstance(max_met, list) and max_met else 'N/A',
            max_met[0].get('fitnessAge', 'N/A') if isinstance(max_met, list) and max_met else 'N/A',
            spo2.get('averageSpO2', 'N/A') if isinstance(spo2, dict) else 'N/A',
            resp.get('sleepAwakeAvgRespirationRate', 'N/A') if isinstance(resp, dict) else 'N/A',
            stats.get('weight', 'N/A')
        ]

    def get_latest_activities(self, limit=5):
        """Fetches recent activities and their details."""
        activities = self.client.get_activities(0, limit)
        summary_rows = []
        strength_rows = []

        for act in activities:
            act_id = act['activityId']
            act_type = act['activityType']['typeKey']
            
            # 1. Basic Summary Info
            summary_rows.append([
                act_id,
                act['startTimeLocal'],
                act['activityName'],
                act_type,
                round(act.get('distance', 0) / 1000, 2),
                str(datetime.timedelta(seconds=int(act.get('duration', 0)))),
                act.get('averageHR', 'N/A'),
                act.get('maxHR', 'N/A'),
                act.get('calories', 'N/A'),
                act.get('aerobicTrainingEffect', 'N/A'),
                act.get('anaerobicTrainingEffect', 'N/A'),
                act.get('vO2MaxValue', 'N/A'),
                act.get('steps', 'N/A')
            ])

            # 2. Strength Deep Dive Info
            if act_type == 'strength_training':
                try:
                    details = self.client.get_activity_details(act_id)
                    sets = details.get('metadataDTO', {}).get('sets', [])
                    for i, s in enumerate(sets):
                        strength_rows.append([
                            act_id,
                            act['startTimeLocal'].split(' ')[0],
                            i + 1,
                            s.get('exerciseName', 'Unknown'),
                            s.get('reps', 0),
                            s.get('weight', 0) / 1000, # Grams to KG
                            s.get('category', 'N/A')
                        ])
                except Exception as e:
                    print(f"Could not get strength details for {act_id}: {e}")

        return summary_rows, strength_rows