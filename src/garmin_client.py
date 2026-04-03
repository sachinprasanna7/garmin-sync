import os
import time
import datetime
from garminconnect import Garmin, GarminConnectAuthenticationError

class GarminSyncClient:
    def __init__(self, email, password, session_dir):
        self.email = email
        self.password = password
        self.session_dir = session_dir  # This will be "/app/secrets"
        self.client = None
        self._login()

    def _login(self):
        """Authenticates using the official SSO flow and json token file."""
        print("Authenticating Garmin client...")
        self.client = Garmin(
            self.email, 
            self.password,
            prompt_mfa=lambda: input("MFA code: ")
        )
        
        # Passes the directory. The library reads/writes garmin_tokens.json here.
        self.client.login(self.session_dir)
        print(f"Session ready ✅ (Tokens managed at '{self.session_dir}/garmin_tokens.json')")

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
                    self._login()
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
    #  Update Activities Daily                                           #
    # ------------------------------------------------------------------ #

    def get_activity_log(self, target_date, limit=8):
        """Fetches the high-level Activity_Log for a specific target date."""
        # Fetch the latest 8 activities as requested
        activities = self._call(self.client.get_activities, 0, limit)
        activity_log = []

        for act in activities:
            # Extract the date and time from startTimeLocal (e.g., "2026-04-01 21:52:53")
            start_time_local = act.get('startTimeLocal', '')
            if not start_time_local:
                continue
                
            activity_date = start_time_local.split(' ')[0]  # Gets "2026-04-01"
            activity_time = start_time_local.split(' ')[1] if len(start_time_local.split(' ')) > 1 else 'N/A'

            # FILTER: Only process if the activity date matches the target_date
            if activity_date != target_date:
                continue

            # Garmin returns speed in meters/second. Convert to Pace (min/km)
            speed_ms = act.get('averageSpeed', 0)
            pace = "N/A"
            if speed_ms and speed_ms > 0:
                pace_sec_per_km = 1000 / speed_ms
                mins, secs = divmod(int(pace_sec_per_km), 60)
                pace = f"{mins}:{secs:02d}"

            activity_log.append([
                act.get('activityId'),
                activity_date,                                                # Date
                activity_time,                                                # Time
                act.get('activityType', {}).get('typeKey', 'unknown'),        # Type
                round(act.get('distance', 0) / 1000, 2),                      # Distance (km)
                str(datetime.timedelta(seconds=int(act.get('duration', 0)))), # Duration (HH:MM:SS)
                pace,                                                         # Pace (min/km)
                act.get('calories', 0),                                       # Calories
                act.get('averageHR', 'N/A'),                                  # Avg HR
                act.get('maxHR', 'N/A'),                                      # Max HR
                act.get('aerobicTrainingEffect', 'N/A'),                      # Aerobic TE
                act.get('steps', 0)                                           # Steps
            ])
            
        return activity_log
    
    def get_strength_log(self, target_date, limit=10):
        """Fetches the detailed strength training log for a target date."""
        # STEP 1: Fetch recent activities to find the strength training IDs
        activities = self._call(self.client.get_activities, 0, limit)
        strength_log = []

        for act in activities:
            start_time_local = act.get('startTimeLocal', '')
            if not start_time_local:
                continue

            activity_date = start_time_local.split(' ')[0]
            act_type = act.get('activityType', {}).get('typeKey', '')

            # STEP 2: Filter for ONLY strength training on our target date
            if activity_date != target_date or act_type != 'strength_training':
                continue

            act_id = act.get('activityId')

            # STEP 3: Now fetch the detailed sets for this specific workout
            try:
                set_data = self._call(self.client.get_activity_exercise_sets, act_id)
                exercise_sets = set_data.get('exerciseSets', [])

                set_number = 1  # We will manually track working sets per workout

                for s in exercise_sets:
                    # We only care about actual lifting, skip the rest periods
                    if s.get('setType') != 'ACTIVE':
                        continue 

                    # Extract exercise name from Garmin's probability array
                    exercises = s.get('exercises', [])
                    exercise_category = 'UNKNOWN'
                    exercise_name = 'UNKNOWN'

                    if exercises and len(exercises) > 0:
                        exercise_category = exercises[0].get('category', 'UNKNOWN')
                        # Sometimes name is null (like for Cardio), so fallback to category
                        exercise_name = exercises[0].get('name') or exercise_category

                    # Garmin stores weight in grams, convert to kg
                    weight_g = s.get('weight')
                    weight_kg = (weight_g / 1000) if weight_g else 0.0

                    # Null check for reps (e.g., timed cardio sets might not have reps)
                    reps = s.get('repetitionCount') or 0

                    strength_log.append([
                        act_id,                                # Activity ID
                        activity_date,                         # Date
                        s.get('startTime').split('T')[1][:8],  # Start Time (extracted from timestamp)
                        set_number,                            # Set Number
                        exercise_category,                     # Broad Category (e.g., BENCH_PRESS)
                        exercise_name,                         # Specific Name (e.g., DUMBBELL_BENCH_PRESS)
                        reps,                                  # Reps
                        weight_kg,                             # Weight (kg)
                        round(s.get('duration', 0), 1)         # Set Duration (seconds)
                    ])

                    set_number += 1

            except Exception as e:
                print(f"Could not fetch strength sets for {act_id}: {e}")

        return strength_log
    

    def get_running_lapwise_log(self, target_date, limit=10):
        """Fetches the ultimate deep-dive running log for a target date."""
        # STEP 1: Fetch recent activities to find the Running IDs
        activities = self._call(self.client.get_activities, 0, limit)
        running_lapwise_log = []

        for act in activities:
            start_time_local = act.get('startTimeLocal', '')
            if not start_time_local:
                continue

            activity_date = start_time_local.split(' ')[0]
            act_type = act.get('activityType', {}).get('typeKey', '')

            # STEP 2: Filter for ONLY running on our target date
            if activity_date != target_date or act_type != 'running':
                continue

            act_id = act.get('activityId')
            activity_time = start_time_local.split(' ')[1] if len(start_time_local.split(' ')) > 1 else 'N/A'

            try:
                # STEP 3: Fetch lap-by-lap splits
                splits_data = self._call(self.client.get_activity_splits, act_id)
                laps = splits_data.get('lapDTOs', [])

                for lap in laps:
                    # Convert raw Average Speed (m/s) to Pace (min/km)
                    speed_ms = lap.get('averageSpeed', 0)
                    pace = "N/A"
                    if speed_ms and speed_ms > 0:
                        pace_sec_per_km = 1000 / speed_ms
                        mins, secs = divmod(int(pace_sec_per_km), 60)
                        pace = f"{mins}:{secs:02d}"

                    # Convert Grade Adjusted Speed (m/s) to GAP (min/km)
                    gap_ms = lap.get('avgGradeAdjustedSpeed', 0)
                    gap_pace = "N/A"
                    if gap_ms and gap_ms > 0:
                        gap_sec_per_km = 1000 / gap_ms
                        mins, secs = divmod(int(gap_sec_per_km), 60)
                        gap_pace = f"{mins}:{secs:02d}"

                    # Format distance and duration
                    lap_distance_km = round(lap.get('distance', 0) / 1000, 2)
                    lap_duration = str(datetime.timedelta(seconds=int(lap.get('duration', 0))))

                    # Build the master row
                    running_lapwise_log.append([
                        act_id,                                # Activity ID
                        activity_date,                         # Date
                        activity_time,                         # Time
                        lap.get('lapIndex'),                   # Lap Number
                        lap_distance_km,                       # Lap Distance (km)
                        lap_duration,                          # Lap Duration (MM:SS)
                        pace,                                  # Average Pace (min/km)
                        gap_pace,                              # Grade Adjusted Pace (min/km)
                        lap.get('averageHR', 'N/A'),           # Avg HR
                        lap.get('maxHR', 'N/A'),               # Max HR
                        lap.get('averageRunCadence', 'N/A'),   # Avg Cadence (spm)
                        lap.get('strideLength', 'N/A'),        # Stride Length (cm)
                        lap.get('groundContactTime', 'N/A'),   # Ground Contact Time (ms)
                        lap.get('verticalOscillation', 'N/A'), # Vertical Oscillation (cm)
                        lap.get('verticalRatio', 'N/A'),       # Vertical Ratio (%)
                        lap.get('averagePower', 'N/A'),        # Running Power (Watts)
                        lap.get('elevationGain', 0),           # Elevation Gain (m)
                        lap.get('calories', 0)                 # Calories per lap
                    ])

            except Exception as e:
                print(f"Could not fetch detailed running splits for {act_id}: {e}")

        return running_lapwise_log
    

    def get_running_master_log(self, target_date, limit=10):
        """Fetches the ultimate top-tier summary for running activities on a target date."""
        activities = self._call(self.client.get_activities, 0, limit)
        running_master_log = []

        # Helper function to convert meters/second to MM:SS pace
        def ms_to_pace(speed_ms):
            if not speed_ms or speed_ms <= 0:
                return "N/A"
            pace_sec_per_km = 1000 / speed_ms
            mins, secs = divmod(int(pace_sec_per_km), 60)
            return f"{mins}:{secs:02d}"

        # Helper function to convert raw seconds to MM:SS (for fastest splits)
        def secs_to_time(secs):
            if not secs or secs <= 0:
                return "N/A"
            mins, s = divmod(int(secs), 60)
            return f"{mins}:{s:02d}"

        for act in activities:
            start_time_local = act.get('startTimeLocal', '')
            if not start_time_local:
                continue

            activity_date = start_time_local.split(' ')[0]
            act_type = act.get('activityType', {}).get('typeKey', '')

            # FILTER: Only process runs on the target date
            if activity_date != target_date or act_type != 'running':
                continue

            # 1. Times & Durations
            activity_time = start_time_local.split(' ')[1] if len(start_time_local.split(' ')) > 1 else 'N/A'
            duration_str = str(datetime.timedelta(seconds=int(act.get('duration', 0))))
            moving_duration_str = str(datetime.timedelta(seconds=int(act.get('movingDuration', 0))))

            # 2. Paces
            avg_pace = ms_to_pace(act.get('averageSpeed', 0))
            max_pace = ms_to_pace(act.get('maxSpeed', 0))
            gap_pace = ms_to_pace(act.get('avgGradeAdjustedSpeed', 0))

            # 3. Time in HR Zones (Garmin returns seconds, converting to minutes for readability)
            z1_mins = round(act.get('hrTimeInZone_1', 0) / 60, 1)
            z2_mins = round(act.get('hrTimeInZone_2', 0) / 60, 1)
            z3_mins = round(act.get('hrTimeInZone_3', 0) / 60, 1)
            z4_mins = round(act.get('hrTimeInZone_4', 0) / 60, 1)
            z5_mins = round(act.get('hrTimeInZone_5', 0) / 60, 1)

            running_master_log.append([
                act.get('activityId'),                                 # 1. Activity ID
                act.get('activityName', 'Running'),                    # 2. Name
                activity_date,                                         # 3. Date
                activity_time,                                         # 4. Time
                round(act.get('distance', 0) / 1000, 2),               # 5. Distance (km)
                duration_str,                                          # 6. Total Time
                moving_duration_str,                                   # 7. Moving Time
                avg_pace,                                              # 8. Avg Pace (min/km)
                gap_pace,                                              # 9. Grade Adjusted Pace
                max_pace,                                              # 10. Max Pace
                act.get('elevationGain', 0),                           # 11. Elevation Gain (m)
                act.get('elevationLoss', 0),                           # 12. Elevation Loss (m)
                act.get('calories', 0),                                # 13. Total Calories
                act.get('waterEstimated', 0),                          # 14. Estimated Sweat Loss (ml)
                
                # --- HEART RATE & EFFORT ---
                act.get('averageHR', 'N/A'),                           # 15. Avg HR
                act.get('maxHR', 'N/A'),                               # 16. Max HR
                z1_mins, z2_mins, z3_mins, z4_mins, z5_mins,           # 17-21. HR Zones (Minutes spent in Z1-Z5)
                
                # --- RUNNING DYNAMICS ---
                act.get('averageRunningCadenceInStepsPerMinute', 0),   # 22. Avg Cadence (spm)
                act.get('maxRunningCadenceInStepsPerMinute', 0),       # 23. Max Cadence
                act.get('avgStrideLength', 0),                         # 24. Stride Length (cm)
                act.get('avgGroundContactTime', 0),                    # 25. Ground Contact Time (ms)
                act.get('avgVerticalOscillation', 0),                  # 26. Vertical Oscillation (cm)
                act.get('avgVerticalRatio', 0),                        # 27. Vertical Ratio (%)
                
                # --- POWER ---
                act.get('avgPower', 0),                                # 28. Avg Power (W)
                act.get('maxPower', 0),                                # 29. Max Power (W)
                
                # --- TRAINING EFFECT & LOAD ---
                act.get('aerobicTrainingEffect', 0),                   # 30. Aerobic TE (0.0 - 5.0)
                act.get('anaerobicTrainingEffect', 0),                 # 31. Anaerobic TE (0.0 - 5.0)
                act.get('trainingEffectLabel', 'N/A'),                 # 32. TE Label (e.g., "AEROBIC_BASE")
                act.get('activityTrainingLoad', 0),                    # 33. Training Load
                act.get('differenceBodyBattery', 0),                   # 34. Body Battery Drain
                
                # --- PERFORMANCE HIGHLIGHTS ---
                secs_to_time(act.get('fastestSplit_1000', 0)),         # 35. Fastest 1km
                secs_to_time(act.get('fastestSplit_1609', 0)),         # 36. Fastest 1 Mile
                secs_to_time(act.get('fastestSplit_5000', 0)),         # 37. Fastest 5k
            ])

        return running_master_log


    