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
        user_summary_data = self._call(self.client.get_user_summary, day)
        user_summary_data_kpis = {
            "Date": user_summary_data.get("calendarDate"),
            "Total Steps": user_summary_data.get("totalSteps", 0),
            "Distance (km)": round(user_summary_data.get("totalDistanceMeters", 0) / 1000, 2),
            "BMR Calories": user_summary_data.get("bmrKilocalories", 0),
            "Active Calories": user_summary_data.get("activeKilocalories", 0),
            "Total Calories": user_summary_data.get("totalKilocalories", 0),
            "Floors Climbed": user_summary_data.get("floorsAscended", 0),
            "Highly Active Seconds": user_summary_data.get("highlyActiveSeconds", 0),
            "Active Seconds": user_summary_data.get("activeSeconds", 0),
            "Sedentary Seconds": user_summary_data.get("sedentarySeconds", 0),
            "Sleeping Seconds": user_summary_data.get("sleepingSeconds", 0),
            "Moderate Intensity Minutes": user_summary_data.get("moderateIntensityMinutes", 0),
            "Vigorous Intensity Minutes": user_summary_data.get("vigorousIntensityMinutes", 0),
            "Min HR": user_summary_data.get("minHeartRate", 'N/A'),
            "Max HR": user_summary_data.get("maxHeartRate", 'N/A'),
            "Resting HR": user_summary_data.get("restingHeartRate", 'N/A'),
            "7 Day Avg Resting HR": user_summary_data.get("lastSevenDaysAverageRestingHeartRate", 'N/A'),
            "Min Average HR": user_summary_data.get("minAvgHeartRate", 'N/A'),
            "Max Average HR": user_summary_data.get("maxAvgHeartRate", 'N/A'),
            "Body Battery Wake Time": user_summary_data.get("bodyBatteryAtWakeTime"),
            "Body Battery Highest": user_summary_data.get("bodyBatteryHighestValue"),
            "Body Battery Lowest": user_summary_data.get("bodyBatteryLowestValue"),
            "Body Battery Charged Value": user_summary_data.get("bodyBatteryChargedValue"),
            "Body Battery Drained Value": user_summary_data.get("bodyBatteryDrainedValue"),
            "Lowest SpO2": user_summary_data.get("lowestSpO2", 'N/A'),
            "Avg SpO2": user_summary_data.get("averageSpo2", 'N/A'),
            "Highest Respiration": user_summary_data.get("highestRespirationValue", 'N/A'),
            "Lowest Respiration": user_summary_data.get("lowestRespirationValue", 'N/A'),
            "Avg Respiration": user_summary_data.get("avgWakingRespirationValue", 'N/A'),
            "Average Stress Level": user_summary_data.get("averageStressLevel", 'N/A'),
            "Max Stress Level": user_summary_data.get("maxStressLevel", 'N/A'),
            "Stress Percentage": user_summary_data.get("stressPercentage", 'N/A'),
            "Resting Stress Percentage": user_summary_data.get("restStressPercentage", 'N/A'),
            "Active Stress Percentage": user_summary_data.get("activeStressPercentage", 'N/A'),
        }

        stats_and_body_data = self._call(self.client.get_stats_and_body, day)
        weight = stats_and_body_data.get("weight", 'N/A')
        user_summary_data_kpis["Weight (kg)"] = round(weight / 1000, 2) if isinstance(weight, (int, float)) else 'N/A'

        hydration_data = self._call(self.client.get_hydration_data, day)
        user_summary_data_kpis["Hydration (ml)"] = hydration_data.get("valueInML", 'N/A')
        user_summary_data_kpis["Daily Average Hydration (ml)"] = hydration_data.get("dailyAverageinML", 'N/A')
        user_summary_data_kpis["Sweat Loss (ml)"] = hydration_data.get("sweatLossInML", 'N/A')

        readiness_data = self._call(self.client.get_training_readiness, day)
        if isinstance(readiness_data, list) and readiness_data:
            readiness_entry = readiness_data[0]
            user_summary_data_kpis["Readiness Score"] = readiness_entry.get("score", 'N/A')
            user_summary_data_kpis["Readiness Level"] = readiness_entry.get("level", 'N/A')
            user_summary_data_kpis["Sleep Score"] = readiness_entry.get("sleepScore", 'N/A')
        

        hrv_data = self._call(self.client.get_hrv_data, day)
        if isinstance(hrv_data, dict):
            hrv_summary = hrv_data.get("hrvSummary", {})
            user_summary_data_kpis["Overnight HRV Avg"] = hrv_summary.get("lastNightAvg", 'N/A')
            user_summary_data_kpis["HRV Status"] = hrv_summary.get("status", 'N/A')
            hrv_baseline = hrv_data.get("baseline", {})
            user_summary_data_kpis["HRV Balanced Low"] = hrv_baseline.get("balancedLow", 'N/A')
            user_summary_data_kpis["HRV Balanced Upper"] = hrv_baseline.get("balancedUpper", 'N/A')

        try:
            # Using the daily aggregation to ensure we get the arrays
            four_weeks_ago = (datetime.date.fromisoformat(day) - datetime.timedelta(days=28)).isoformat()
            lactate_data = self._call(self.client.get_lactate_threshold, latest=False, start_date=four_weeks_ago, end_date=day, aggregation='daily')
            
            if lactate_data:
                if "heart_rate" in lactate_data and lactate_data["heart_rate"]:
                    user_summary_data_kpis["Lactate Threshold HR"] = lactate_data["heart_rate"][-1].get("value", 'N/A')
                if "power" in lactate_data and lactate_data["power"]:
                    user_summary_data_kpis["Lactate Threshold Power"] = lactate_data["power"][-1].get("value", 'N/A')
        except Exception as e:
            print(f"Skipping Lactate Threshold: {e}")

        # 2. Training Status, VO2 Max, and Load Balance
        try:
            status_payload = self._call(self.client.get_training_status, day)
            
            if isinstance(status_payload, dict):
                # A. VO2 Max
                vo2_data = status_payload.get("mostRecentVO2Max", {}).get("generic", {})
                user_summary_data_kpis["VO2 Max"] = vo2_data.get("vo2MaxPreciseValue", 'N/A')

                # B. Training Status & ACWR (Bypass dynamic Device ID)
                training_status_dict = status_payload.get("mostRecentTrainingStatus", {}).get("latestTrainingStatusData", {})
                if training_status_dict:
                    status_data = list(training_status_dict.values())[0] # Grabs the first device
                    user_summary_data_kpis["Training Status"] = status_data.get("trainingStatusFeedbackPhrase", 'N/A')
                    
                    acute_load_dto = status_data.get("acuteTrainingLoadDTO", {})
                    user_summary_data_kpis["Acute Load"] = acute_load_dto.get("dailyTrainingLoadAcute", 'N/A')
                    user_summary_data_kpis["ACWR"] = acute_load_dto.get("dailyAcuteChronicWorkloadRatio", 'N/A')

                # C. Training Load Balance
                load_balance_dict = status_payload.get("mostRecentTrainingLoadBalance", {}).get("metricsTrainingLoadBalanceDTOMap", {})
                if load_balance_dict:
                    load_balance = list(load_balance_dict.values())[0] # Grabs the first device
                    user_summary_data_kpis["Load Focus"] = load_balance.get("trainingBalanceFeedbackPhrase", 'N/A')
                    user_summary_data_kpis["Low Aerobic Load"] = round(load_balance.get("monthlyLoadAerobicLow", 0), 1)
                    user_summary_data_kpis["High Aerobic Load"] = round(load_balance.get("monthlyLoadAerobicHigh", 0), 1)
                    user_summary_data_kpis["Anaerobic Load"] = round(load_balance.get("monthlyLoadAnaerobic", 0), 1)

        except Exception as e:
            print(f"Skipping Training Status: {e}")

        
        # ---------------------------------------------------------
        # SLEEP STAGES & TIMES (Appending to user_summary_data_kpis)
        # ---------------------------------------------------------
        try:
            import datetime
            sleep_data = self._call(self.client.get_sleep_data, day)
            if isinstance(sleep_data, dict):
                daily_sleep = sleep_data.get("dailySleepDTO", {})
                
                # Helper function to convert seconds to hours
                def secs_to_hrs(secs):
                    return round(secs / 3600, 2) if secs else 0

                # 1. Sleep Durations
                user_summary_data_kpis["Total Sleep (hrs)"] = secs_to_hrs(daily_sleep.get("sleepTimeSeconds"))
                user_summary_data_kpis["Deep Sleep (hrs)"] = secs_to_hrs(daily_sleep.get("deepSleepSeconds"))
                user_summary_data_kpis["Light Sleep (hrs)"] = secs_to_hrs(daily_sleep.get("lightSleepSeconds"))
                user_summary_data_kpis["REM Sleep (hrs)"] = secs_to_hrs(daily_sleep.get("remSleepSeconds"))
                user_summary_data_kpis["Awake Time (hrs)"] = secs_to_hrs(daily_sleep.get("awakeSleepSeconds"))
                
                # 2. Bedtime and Wake Time
                start_ms = daily_sleep.get("sleepStartTimestampGMT")
                end_ms = daily_sleep.get("sleepEndTimestampGMT")
                
                if start_ms and end_ms:
                    # Convert Garmin's millisecond timestamps to readable times
                    bedtime = datetime.datetime.fromtimestamp(start_ms / 1000).strftime('%I:%M %p')
                    waketime = datetime.datetime.fromtimestamp(end_ms / 1000).strftime('%I:%M %p')
                    
                    user_summary_data_kpis["Bedtime"] = bedtime
                    user_summary_data_kpis["Wake Time"] = waketime

                # 3. Bonus
                user_summary_data_kpis["Sleep Body Battery Recharge"] = sleep_data.get("bodyBatteryChange", 'N/A')
                
        except Exception as e:
            print(f"Skipping Sleep Data: {e}")


        return user_summary_data_kpis

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