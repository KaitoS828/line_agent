"""天気情報アクション — wttr.in API（キー不要）"""

import httpx
from config import WEATHER_CITY


def get_weather(city: str = "") -> str:
    """天気情報を取得"""
    city = city or WEATHER_CITY
    try:
        resp = httpx.get(
            f"https://wttr.in/{city}?format=j1",
            timeout=10,
            headers={"Accept-Language": "ja"},
        )
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current_condition", [{}])[0]
        today = data.get("weather", [{}])[0]

        temp = current.get("temp_C", "?")
        desc_ja = current.get("lang_ja", [{}])
        desc = desc_ja[0].get("value", current.get("weatherDesc", [{}])[0].get("value", "")) if desc_ja else current.get("weatherDesc", [{}])[0].get("value", "")
        humidity = current.get("humidity", "?")
        max_temp = today.get("maxtempC", "?")
        min_temp = today.get("mintempC", "?")

        return f"🌤 {city}: {temp}°C {desc} / 最高 {max_temp}°C 最低 {min_temp}°C / 湿度 {humidity}%"
    except Exception as e:
        return f"🌤 天気情報を取得できませんでした: {e}"
