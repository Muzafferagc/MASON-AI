"""
weather.py - Hava durumu (Open-Meteo, tamamen UCRETSIZ, API anahtari GEREKMEZ)

Open-Meteo (https://open-meteo.com) acik ve ucretsiz bir hava durumu servisidir;
kayit/anahtar istemez. Enlem-boylam ile anlik sicaklik + gunun en dusuk/yuksek
sicakligi + hava durumu kodunu ceker. Internet yoksa sessizce None doner
(brifing yine calisir, sadece hava satiri atlanir).
"""
import requests

# WMO hava durumu kodu -> Turkce aciklama + emoji
_WMO = {
    0: ("açık", "☀️"), 1: ("çoğunlukla açık", "🌤️"), 2: ("parçalı bulutlu", "⛅"),
    3: ("kapalı", "☁️"), 45: ("sisli", "🌫️"), 48: ("kırağılı sis", "🌫️"),
    51: ("hafif çisenti", "🌦️"), 53: ("çisenti", "🌦️"), 55: ("yoğun çisenti", "🌦️"),
    61: ("hafif yağmur", "🌧️"), 63: ("yağmur", "🌧️"), 65: ("şiddetli yağmur", "🌧️"),
    66: ("dondurucu yağmur", "🌧️"), 67: ("şiddetli dondurucu yağmur", "🌧️"),
    71: ("hafif kar", "🌨️"), 73: ("kar", "🌨️"), 75: ("yoğun kar", "❄️"),
    77: ("kar taneleri", "🌨️"), 80: ("hafif sağanak", "🌦️"), 81: ("sağanak", "🌧️"),
    82: ("şiddetli sağanak", "⛈️"), 85: ("hafif kar sağanağı", "🌨️"),
    86: ("yoğun kar sağanağı", "❄️"), 95: ("gök gürültülü fırtına", "⛈️"),
    96: ("dolu ile fırtına", "⛈️"), 99: ("şiddetli dolu ile fırtına", "⛈️"),
}


def describe_code(code: int) -> tuple[str, str]:
    return _WMO.get(int(code), ("değişken", "🌡️"))


def get_weather(config: dict) -> dict | None:
    """Anlik hava durumunu dondurur veya None (internet yok / hata).
    Donen: {city, temp, code, desc, emoji, tmin, tmax}."""
    try:
        lat = float(config.get("weather_lat", 36.90))
        lon = float(config.get("weather_lon", 30.70))
    except (TypeError, ValueError):
        lat, lon = 36.90, 30.70
    city = config.get("weather_city", "Antalya")
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "auto", "forecast_days": 1,
            },
            timeout=12,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        cur = data.get("current", {})
        daily = data.get("daily", {})
        code = int(cur.get("weather_code", 0))
        desc, emoji = describe_code(code)
        return {
            "city": city,
            "temp": round(float(cur.get("temperature_2m"))),
            "code": code, "desc": desc, "emoji": emoji,
            "tmax": round(float(daily.get("temperature_2m_max", [None])[0])),
            "tmin": round(float(daily.get("temperature_2m_min", [None])[0])),
        }
    except Exception:
        return None


def format_weather(config: dict) -> str | None:
    """Hava durumunu tek satir metne cevirir (brifing icin)."""
    w = get_weather(config)
    if not w:
        return None
    return (f"{w['emoji']} {w['city']}: {w['temp']}°C, {w['desc']} "
            f"(en düşük {w['tmin']}°, en yüksek {w['tmax']}°)")
