import os
import time
import datetime
from garminconnect import Garmin, GarminConnectAuthenticationError
import json

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

    def get_everything_daily(self, day, DAILY_HEADERS):
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

                    # change it to indian time by adding 5:30 to the time
                    bedtime_dt = datetime.datetime.fromtimestamp(start_ms / 1000) + datetime.timedelta(hours=5, minutes=30)
                    waketime_dt = datetime.datetime.fromtimestamp(end_ms / 1000) + datetime.timedelta(hours=5, minutes=30)
                    
                    user_summary_data_kpis["Bedtime"] = bedtime_dt.strftime('%I:%M %p')
                    user_summary_data_kpis["Wake Time"] = waketime_dt.strftime('%I:%M %p')

                # 3. Bonus
                user_summary_data_kpis["Sleep Body Battery Recharge"] = sleep_data.get("bodyBatteryChange", 'N/A')
                
        except Exception as e:
            print(f"Skipping Sleep Data: {e}")

        # convert the json into a simple list of kpis in the order of the headers
        return [user_summary_data_kpis.get(header, 'N/A') for header in DAILY_HEADERS]

    # ------------------------------------------------------------------ #
    #  Update Activities Daily                                           #
    # ------------------------------------------------------------------ #

    def get_activity_log(self, target_date, limit=50):
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
    
    def get_strength_log(self, target_date, limit=25):
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
    

    def get_running_lapwise_log(self, target_date, limit=50):
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
    

    def get_running_master_log(self, target_date, limit=50):
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

            start_lat = act.get('startLatitude')
            start_lon = act.get('startLongitude')

            # FILTER: Only process runs on the target date
            if activity_date != target_date or act_type != 'running':
                continue

            # 1. Times & Durations
            activity_time = start_time_local.split(' ')[1] if len(start_time_local.split(' ')) > 1 else 'N/A'
            duration_str = str(datetime.timedelta(seconds=int(act.get('duration', 0))))
            moving_duration_str = str(datetime.timedelta(seconds=int(act.get('movingDuration', 0))))

            # --- NEW: Surgically Extract Walk Metrics ---
            act_id = act.get('activityId')
            walk_duration_secs = 0
            walk_distance_m = 0.0

            try:
                # Get the specific activity summary that contains the splitSummaries array
                full_act = self._call(self.client.get_activity, act_id)
                splits = full_act.get('splitSummaries', [])
                
                # Loop through the array to find the 'WALK' bucket
                for split in splits:
                    if split.get('splitType') == 'RWD_WALK':
                        walk_duration_secs = split.get('duration', 0)
                        walk_distance_m = split.get('distance', 0)
                        break # Found it, stop looking
                        
            except Exception as e:
                print(f"⚠️ Could not fetch walk splits for {act_id}: {e}")

            # Format the duration cleanly
            walk_duration_str = str(datetime.timedelta(seconds=int(walk_duration_secs))) if walk_duration_secs else "0:00:00"

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

            summary_dto = full_act.get('summaryDTO', {}) if 'full_act' in locals() else {}

            # Garmin stores RPE as 10-100, we divide by 10 to get 1-10
            rpe_raw = summary_dto.get('directWorkoutRpe') or act.get('directWorkoutRpe')
            rpe = int(rpe_raw / 10) if rpe_raw is not None else 'N/A'
            
            # Garmin stores Feel as 0-100 (0=Very Weak, 100=Very Strong)
            feel_raw = summary_dto.get('directWorkoutFeel') or act.get('directWorkoutFeel')
            feel = int(feel_raw) if feel_raw is not None else 'N/A'
            
            # Stamina remaining at the end of the run
            end_stamina = summary_dto.get('endPotentialStamina') or act.get('endPotentialStamina') or 'N/A'
            
            # Normalized Power
            np_power = summary_dto.get('normalizedPower') or act.get('normalizedPower') or 'N/A'

            run_notes = act.get('description', '')

            running_master_log.append([
                act.get('activityId'),                                 # 1. Activity ID
                act.get('activityName', 'Running'),                    # 2. Name
                start_lat, 
                start_lon,                                                       # Bonus: Start Coordinates (for potential weather API integration)
                activity_date,                                         # 3. Date
                activity_time,                                         # 4. Time
                round(act.get('distance', 0) / 1000, 2),               # 5. Distance (km)

                duration_str,                                          # 6. Total Time
                moving_duration_str,                                   # 7. Moving Time
                avg_pace,                                              # 8. Avg Pace (min/km)
                gap_pace,                                              # 9. Grade Adjusted Pace
                max_pace,                                              # 10. Max Pace
                walk_duration_str,                                        # 11. Walk Duration
                walk_distance_m,                                        # 12. Walk Distance (km)
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

                rpe,                                                    # 35. RPE (Rate of Perceived Exertion)
                feel,                                                   # 36. Feel (Garmin's subjective strength rating)
                end_stamina,                                            # 37. Stamina Remaining at End of Run
                np_power,                                               # 38. Normalized Power (Watts)
                
                # --- PERFORMANCE HIGHLIGHTS ---
                secs_to_time(act.get('fastestSplit_1000', 0)),         # 35. Fastest 1km
                secs_to_time(act.get('fastestSplit_1609', 0)),         # 36. Fastest 1 Mile
                secs_to_time(act.get('fastestSplit_5000', 0)),         # 37. Fastest 5k

                run_notes                                               # 38. User Notes
            ])

        return running_master_log
    

    def get_lifestyle_log(self, target_date):
        """Fetches the Lifestyle Journaling (Behaviors) data for a target date."""
        try:
            data = self._call(self.client.get_lifestyle_logging_data, target_date)
            reports = data.get("dailyLogsReport", [])
            
            behavior_rows = []
            for item in reports:
                # Convert the 'details' list/dict into a string so Sheets can accept it
                details_json = json.dumps(item.get("details", []))
                
                behavior_rows.append([
                    target_date,
                    item.get("name"),       # e.g., "Habit Streak"
                    item.get("logStatus"), # "YES"/"NO"
                    item.get("category"),  # e.g., "LIFESTYLE"
                    details_json           # This is now a String, not a List!
                ])
            return behavior_rows
        except Exception as e:
            print(f"⚠️ Could not fetch lifestyle behaviors: {e}")
            return []

    from datetime import datetime, timedelta

    def get_strength_log(self, target_date, limit=25):
        """Fetches the detailed strength training log for a target date."""
        
        # -------------------------------------------------------------------------
        # Conversion Table Definition (Plate, Weight lbs, Weight kg)
        # -------------------------------------------------------------------------
        CONVERSION_TABLE = [
            {"plate": 1,  "lbs": 135, "kg": 5.90},
            {"plate": 2,  "lbs": 188, "kg": 8.16},
            {"plate": 3,  "lbs": 23,  "kg": 10.43},
            {"plate": 4,  "lbs": 28,  "kg": 12.70},
            {"plate": 5,  "lbs": 33,  "kg": 14.97},
            {"plate": 6,  "lbs": 43,  "kg": 19.50},
            {"plate": 7,  "lbs": 53,  "kg": 24.04},
            {"plate": 8,  "lbs": 63,  "kg": 28.58},
            {"plate": 9,  "lbs": 73,  "kg": 33.11},
            {"plate": 10, "lbs": 83,  "kg": 37.65},
            {"plate": 11, "lbs": 93,  "kg": 42.18},
            {"plate": 12, "lbs": 103, "kg": 46.72},
            {"plate": 13, "lbs": 113, "kg": 51.26},
            {"plate": 14, "lbs": 123, "kg": 55.79},
            {"plate": 15, "lbs": 133, "kg": 60.33},
            {"plate": 16, "lbs": 148, "kg": 67.13},
            {"plate": 17, "lbs": 163, "kg": 73.94},
            {"plate": 18, "lbs": 178, "kg": 80.74},
            {"plate": 19, "lbs": 193, "kg": 87.54},
            {"plate": 20, "lbs": 208, "kg": 94.35},
        ]

        # Categorized exercise lists
        kg_exercise = [
            'BENCH_PRESS',
            'SEATED_DUMBBELL_SHOULDER_PRESS',
            'BARBELL_BICEPS_CURL',
            'LATERAL_RAISE'
        ]

        lbs_exercise = [
            'LAT_PULLDOWN',
            'SEATED_CABLE_ROW',
            'TRICEPS_PRESSDOWN'
        ]

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

            # STEP 3: Fetch the detailed sets for this specific workout
            try:
                set_data = self._call(self.client.get_activity_exercise_sets, act_id)
                exercise_sets = set_data.get('exerciseSets', [])

                set_number = 1  # Track working sets per workout

                for s in exercise_sets:
                    # Skip non-active rest periods
                    if s.get('setType') != 'ACTIVE':
                        continue 

                    # Extract exercise name from Garmin's structure
                    exercises = s.get('exercises', [])
                    exercise_category = 'UNKNOWN'
                    exercise_name = 'UNKNOWN'

                    if exercises and len(exercises) > 0:
                        exercise_category = exercises[0].get('category', 'UNKNOWN')
                        exercise_name = exercises[0].get('name') or exercise_category

                    # --- 1. TIMEZONE CONVERSION (GMT -> IST in 12-hr format) ---
                    start_time_raw = s.get('startTime')  # e.g., '2026-03-31T08:53:20.0'
                    if start_time_raw and 'T' in start_time_raw:
                        time_str = start_time_raw.split('T')[1][:8]
                        
                        # Use an alias (dt and td) to completely avoid naming collisions 
                        from datetime import datetime as dt, timedelta as td
                        
                        gmt_time = dt.strptime(time_str, '%H:%M:%S')
                        # Convert to IST (+5 hours 30 mins)
                        ist_time = gmt_time + td(hours=5, minutes=30)
                        formatted_time = ist_time.strftime('%I:%M:%S %p').lstrip('0')
                    else:
                        formatted_time = ''

                    # --- 2. WEIGHT CALCULATIONS ---
                    weight_g = s.get('weight')
                    weight_kg = (weight_g / 1000) if weight_g else 0.0

                    final_weight_kg = 0.0
                    final_weight_lbs = 0.0

                    # Check exercise category logic
                    if exercise_name in kg_exercise:
                        final_weight_kg = weight_kg
                        final_weight_lbs = round(final_weight_kg * 2.205, 2)

                    elif exercise_name in lbs_exercise:
                        if weight_kg > 0:
                            # Find closest entry in conversion sheet by matching minimal kg distance
                            closest_match = min(
                                CONVERSION_TABLE,
                                key=lambda x: abs(x['kg'] - weight_kg)
                            )
                            final_weight_kg = closest_match['kg']
                            final_weight_lbs = float(closest_match['lbs'])

                    else:
                        # Default for unrecognized exercises
                        final_weight_kg = 0.0
                        final_weight_lbs = 0.0

                    reps = s.get('repetitionCount') or 0

                    # --- 3. APPEND TO OUTPUT ROW ---
                    strength_log.append([
                        act_id,                                # Activity ID
                        activity_date,                         # Date
                        formatted_time,                        # Start Time (IST 12-hr format, e.g. "2:23:20 PM")
                        set_number,                            # Set Number
                        exercise_category,                     # Broad Category
                        exercise_name,                         # Specific Name
                        reps,                                  # Reps
                        weight_kg,                             # Raw Weight (kg)
                        round(s.get('duration', 0), 1),        # Set Duration (seconds)
                        final_weight_kg,                       # Final Weight (kg)
                        final_weight_lbs                        # Final Weight (lbs)
                    ])

                    set_number += 1

            except Exception as e:
                print(f"Could not fetch strength sets for {act_id}: {e}")

        return strength_log
            