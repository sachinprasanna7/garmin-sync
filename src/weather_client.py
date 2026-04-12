import requests

class WeatherClient:
    def get_run_weather(self, date_str, time_str, lat, lon):
        if not lat or not lon:
            return "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"

        try:
            hour = int(time_str.split(':')[0])
            
            # Added dew_point, apparent_temperature, precipitation, and wind_speed
            url = (f"https://api.open-meteo.com/v1/forecast?"
                   f"latitude={lat}&longitude={lon}&"
                   f"start_date={date_str}&end_date={date_str}&"
                   f"hourly=temperature_2m,relative_humidity_2m,dew_point_2m,"
                   f"apparent_temperature,precipitation,wind_speed_10m")
            
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            # Extract all 6 metrics
            temp = data['hourly']['temperature_2m'][hour]
            hum = data['hourly']['relative_humidity_2m'][hour]
            dew = data['hourly']['dew_point_2m'][hour]
            feels_like = data['hourly']['apparent_temperature'][hour]
            precip = data['hourly']['precipitation'][hour]
            wind = data['hourly']['wind_speed_10m'][hour]

            return temp, hum, dew, feels_like, precip, wind
            
        except Exception as e:
            print(f"⚠️ Weather error at {lat}, {lon}: {e}")
            return "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"