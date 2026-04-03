import os
import time
import datetime
from garminconnect import Garmin, GarminConnectAuthenticationError
import cloudscraper


class GarminSyncClient:
    def __init__(self, email, password, session_dir):
        self.email = email
        self.password = password
        # session_dir is a DIRECTORY now, e.g. "secrets/garth_tokens"
        # Garth stores multiple token files inside it (not a single .json)
        self.session_dir = session_dir
        self.client = None
        self._init_client()

    def _init_client(self):
        """Try restoring from Garth token dir first, fresh login only if needed."""
        if os.path.isdir(self.session_dir):
            try:
                print("Loading saved Garth tokens...")
                self.client = Garmin()
                self.client.login(tokenstore=self.session_dir)
                print("Session restored ✅ (no login request made)")
                return
            except Exception as e:
                print(f"Token restore failed ({e}), doing fresh login...")

        self._fresh_login()

    def _fresh_login(self):
        """Full credential login — only runs when tokens are missing or expired (~1 year)."""
        print("Logging in with credentials (this may trigger MFA)...")
        self.client = Garmin(self.email, self.password)
        
        # --- THE CLOUDSCRAPER MONKEY PATCH ---
        # Cloudflare blocks standard Python requests. We dynamically swap out 
        # Garth's network session for a Cloudscraper session that mimics Chrome.
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        self.client.garth.sess = scraper
        # ------------------------------------
        
        self.client.login()
        # Garth dumps a directory of token files, valid for ~1 year
        os.makedirs(self.session_dir, exist_ok=True)
        self.client.garth.dump(self.session_dir)
        print(f"Tokens saved to '{self.session_dir}' ✅ (won't login again for ~1 year)")

    def _call(self, fn, *args, **kwargs):
        """
        Wraps every API call with:
        - One auth-error retry (re-logins and retries once)
        - One 429 retry (waits 60s then retries once)
        """
        for attempt in range(2):
            try:
                return fn(*args, **kwargs)
            except GarminConnectAuthenticationError:
                if attempt == 0:
                    print("Auth error — refreshing tokens and retrying...")
                    self._fresh_login()
                else:
                    raise
            except Exception as e:
                if "429" in str(e) and attempt == 0:
                    print("Rate limited (429) — waiting 60s before retry...")
                    time.sleep(60)
                else:
                    raise

    # ------------------------------------------------------------------ #
    #  Daily Metrics                                                       #
    # ------------------------------------------------------------------ #

    def get_everything_daily(self, day):
        """Fetches a broad set of daily metrics from multiple endpoints."""
        stats     = self._call(self.client.get_stats_and_body, day)
        readiness = self._call(self.client.get_training_readiness, day)
        status    = self._call(self.client.get_training_status, day)
        sleep     = self._call(self.client.get_sleep_data, day)
        hydration = self._call(self.client.get_hydration_data, day)
        rhr       = self._call(self.client.get_rhr_day, day)
        spo2      = self._call(self.client.get_spo2_data, day)
        resp      = self._call(self.client.get_respiration_data, day)
        max_met   = self._call(self.client.get_max_metrics, day)

        rhr_value = (
            rhr.get('allMetrics', {})
               .get('metricsMap', {})
               .get('WELLNESS_RESTING_HEART_RATE', [{}])[0]
               .get('value', 'N/A')
            if isinstance(rhr, dict) else 'N/A'
        )

        return [
            day,
            stats.get('totalSteps', 0),
            stats.get('totalDistanceMeters', 0) / 1000,
            stats.get('activeKilocalories', 0),
            stats.get('floorsClimbed', 0),
            rhr_value,
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
            stats.get('weight', 'N/A'),
        ]

    # ------------------------------------------------------------------ #
    #  Activities                                                          #
    # ------------------------------------------------------------------ #

    def get_latest_activities(self, limit=5):
        """Fetches recent activities and their details."""
        activities = self._call(self.client.get_activities, 0, limit)
        summary_rows = []
        strength_rows = []

        for act in activities:
            act_id   = act['activityId']
            act_type = act['activityType']['typeKey']

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
                act.get('steps', 'N/A'),
            ])

            if act_type == 'strength_training':
                try:
                    details = self._call(self.client.get_activity_details, act_id)
                    sets = details.get('metadataDTO', {}).get('sets', [])
                    for i, s in enumerate(sets):
                        strength_rows.append([
                            act_id,
                            act['startTimeLocal'].split(' ')[0],
                            i + 1,
                            s.get('exerciseName', 'Unknown'),
                            s.get('reps', 0),
                            s.get('weight', 0) / 1000,  # grams → kg
                            s.get('category', 'N/A'),
                        ])
                except Exception as e:
                    print(f"Could not get strength details for {act_id}: {e}")

        return summary_rows, strength_rows