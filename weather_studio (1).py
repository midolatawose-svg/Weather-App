"""Weather Studio - a modern weather dashboard powered by OpenWeather.

Uses only the Python standard library (Tkinter + urllib).
You need a free OpenWeather API key: https://openweathermap.org/api
(New keys can take up to a couple of hours to activate.)
"""
import json
import queue
import threading
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox

# ---------------------------------------------------------------- palette
BG = "#0B1220"
CARD = "#131C2E"
CARD2 = "#1A2744"
TILE = "#1B2640"
BORDER = "#22304D"
ACCENT = "#5B8CFF"
ACCENT_HOVER = "#7AA2FF"
TEXT = "#E8EEFA"
MUTED = "#7F8CA8"
GOLD = "#FFC83D"
RED = "#FF6B6B"
FONT = "Segoe UI"
EMOJI_FONT = "Segoe UI Emoji"

CONFIG_PATH = Path.home() / ".weather_studio.json"
API_BASE = "https://api.openweathermap.org"
DEFAULT_API_KEY = "5f719ce4af30e9cfc0db46ec0019c2c4"


# ---------------------------------------------------------------- config
def load_config():
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(data):
    try:
        CONFIG_PATH.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


config = load_config()

# ---------------------------------------------------------------- state
units = config.get("units", "metric")  # "metric" or "imperial"
current_place = None  # dict with name/lat/lon
result_queue = queue.Queue()


# ---------------------------------------------------------------- API
def get_json(path, params):
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "WeatherStudio/2.0"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = ""
        try:
            message = json.loads(exc.read().decode("utf-8")).get("message", "")
        except Exception:
            pass
        if exc.code == 401:
            raise RuntimeError(
                "OpenWeather rejected the API key (401). Check it was copied correctly "
                "and that it is active - new keys can take a while to activate."
            ) from exc
        if exc.code == 429:
            raise RuntimeError("Too many requests (429). Wait a moment and try again.") from exc
        raise RuntimeError(f"HTTP {exc.code}: {message or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not connect. Check your internet connection. ({exc.reason})") from exc


def geocode(city, key):
    results = get_json("/geo/1.0/direct", {"q": city, "limit": 1, "appid": key})
    if not results:
        raise RuntimeError("No matching city found. Try adding the country, e.g. 'Sydney, AU'.")
    place = results[0]
    parts = [place.get("name", city)]
    if place.get("state") and place["state"] != parts[0]:
        parts.append(place["state"])
    if place.get("country"):
        parts.append(place["country"])
    return {"name": ", ".join(parts), "lat": place["lat"], "lon": place["lon"]}


def fetch_all(city, key, unit_system, place=None):
    place = place or geocode(city, key)
    params = {"lat": place["lat"], "lon": place["lon"], "appid": key, "units": unit_system}
    current = get_json("/data/2.5/weather", params)
    forecast = get_json("/data/2.5/forecast", params)
    return {"place": place, "current": current, "forecast": forecast, "units": unit_system}


def worker(city, key, unit_system, place):
    try:
        result_queue.put(("ok", fetch_all(city, key, unit_system, place)))
    except Exception as exc:
        result_queue.put(("err", str(exc)))


# ---------------------------------------------------------------- helpers
def icon_for(code):
    mapping = {
        "01d": "☀️", "01n": "🌙", "02d": "🌤️", "02n": "☁️", "03d": "⛅", "03n": "☁️",
        "04d": "☁️", "04n": "☁️", "09d": "🌧️", "09n": "🌧️", "10d": "🌦️", "10n": "🌧️",
        "11d": "⛈️", "11n": "⛈️", "13d": "❄️", "13n": "❄️", "50d": "🌫️", "50n": "🌫️",
    }
    return mapping.get(code, "🌤️")


def local_time(ts, tz_offset):
    return datetime.fromtimestamp(ts + tz_offset, tz=timezone.utc)


def unit_symbols(unit_system):
    return ("°C", "km/h", "km") if unit_system == "metric" else ("°F", "mph", "mi")


def daily_summary(forecast, tz_offset):
    """Collapse OpenWeather's 3-hourly forecast into one entry per day."""
    days = defaultdict(list)
    for item in forecast.get("list", []):
        days[local_time(item["dt"], tz_offset).date()].append(item)
    summary = []
    for day in sorted(days):
        items = days[day]
        midday = min(items, key=lambda i: abs(local_time(i["dt"], tz_offset).hour - 13))
        weather = midday["weather"][0]
        summary.append({
            "date": day,
            "high": max(i["main"]["temp_max"] for i in items),
            "low": min(i["main"]["temp_min"] for i in items),
            "pop": max(i.get("pop", 0) for i in items),
            "icon": weather["icon"].replace("n", "d"),
            "desc": weather["description"].title(),
        })
    return summary


# ---------------------------------------------------------------- widgets
class RoundCard(tk.Canvas):
    """A rounded rectangle you pack/grid like a frame; put content in .body."""

    def __init__(self, parent, fill=CARD, radius=20, pad=18, outline=BORDER, **kw):
        super().__init__(parent, bg=parent.cget("bg"), highlightthickness=0, bd=0, **kw)
        self.fill, self.radius, self.pad, self.outline = fill, radius, pad, outline
        self.body = tk.Frame(self, bg=fill)
        self.win = self.create_window(pad, pad, window=self.body, anchor="nw")
        self.bind("<Configure>", self._redraw)
        self.body.bind("<Configure>", lambda e: self.configure(height=e.height + 2 * self.pad))

    def _redraw(self, event):
        self.delete("bg")
        x1, y1, x2, y2, r = 1, 1, event.width - 1, event.height - 1, self.radius
        points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
                  x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        self.create_polygon(points, smooth=True, fill=self.fill, outline=self.outline, tags="bg")
        self.tag_lower("bg")
        self.itemconfigure(self.win, width=max(event.width - 2 * self.pad, 1))


def lab(parent, text, size=11, color=TEXT, bold=False, **kw):
    bg = kw.pop("bg", parent.cget("bg"))
    return tk.Label(parent, text=text, bg=bg, fg=color,
                    font=(FONT, size, "bold" if bold else "normal"), **kw)


def pill_button(parent, text, command, bg=ACCENT, hover=ACCENT_HOVER, fg="#FFFFFF"):
    btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                    activebackground=hover, activeforeground=fg, relief="flat", bd=0,
                    padx=22, pady=11, font=(FONT, 10, "bold"), cursor="hand2")
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover) if btn["state"] == "normal" else None)
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    return btn


def styled_entry(parent, **kw):
    return tk.Entry(parent, font=(FONT, 11), relief="flat", bg=CARD2, fg=TEXT,
                    insertbackground=TEXT, highlightthickness=1, highlightbackground=BORDER,
                    highlightcolor=ACCENT, **kw)


# ---------------------------------------------------------------- window
root = tk.Tk()
root.title("Weather Studio")
root.geometry("1100x780")
root.minsize(920, 700)
root.configure(bg=BG)

outer = tk.Frame(root, bg=BG)
outer.pack(fill="both", expand=True, padx=24, pady=(20, 8))

# Header
header = tk.Frame(outer, bg=BG)
header.pack(fill="x", pady=(0, 14))
lab(header, "Weather Studio", 22, TEXT, True).pack(side="left")
lab(header, "Powered by OpenWeather", 9, MUTED).pack(side="left", padx=(12, 0), pady=(10, 0))
unit_btn = pill_button(header, "°C" if units == "metric" else "°F", lambda: toggle_units(),
                       bg=CARD2, hover=BORDER)
unit_btn.pack(side="right")

# Search bar
search_card = RoundCard(outer, fill=CARD, radius=18, pad=14)
search_card.pack(fill="x", pady=(0, 14))
sb = search_card.body
sb.grid_columnconfigure(0, weight=3)
sb.grid_columnconfigure(1, weight=2)
city_entry = styled_entry(sb)
city_entry.insert(0, config.get("city", "Sydney, AU"))
city_entry.grid(row=0, column=0, sticky="ew", ipady=9, padx=(0, 10))
key_entry = styled_entry(sb, show="•")
key_entry.insert(0, config.get("api_key") or DEFAULT_API_KEY)
key_entry.grid(row=0, column=1, sticky="ew", ipady=9, padx=(0, 10))
search_btn = pill_button(sb, "Search", lambda: search_weather())
search_btn.grid(row=0, column=2)
lab(sb, "City (optionally with country code)", 8, MUTED, bg=CARD).grid(row=1, column=0, sticky="w", pady=(4, 0))
hint_row = tk.Frame(sb, bg=CARD)
hint_row.grid(row=1, column=1, sticky="w", pady=(4, 0))
lab(hint_row, "OpenWeather API key", 8, MUTED, bg=CARD).pack(side="left")
remember_var = tk.BooleanVar(value=False)
tk.Checkbutton(hint_row, text="remember", variable=remember_var, bg=CARD, fg=MUTED,
               activebackground=CARD, activeforeground=TEXT, selectcolor=CARD2,
               font=(FONT, 8), bd=0, highlightthickness=0).pack(side="left", padx=(10, 0))

# Hero card
hero = RoundCard(outer, fill=CARD2, radius=26, pad=26, outline="#2B3C66")
hero.pack(fill="x", pady=(0, 14))
hb = hero.body
hb.grid_columnconfigure(0, weight=1)
hb.grid_columnconfigure(1, weight=1)

left = tk.Frame(hb, bg=CARD2)
left.grid(row=0, column=0, sticky="nw")
lab(left, "CURRENT WEATHER", 9, ACCENT_HOVER, True, bg=CARD2).pack(anchor="w")
location_label = lab(left, "Search for a city", 20, TEXT, True, bg=CARD2)
location_label.pack(anchor="w", pady=(6, 0))
time_label = lab(left, "", 10, MUTED, bg=CARD2)
time_label.pack(anchor="w")
temp_row = tk.Frame(left, bg=CARD2)
temp_row.pack(anchor="w", pady=(12, 0))
weather_icon = tk.Label(temp_row, text="☀️", bg=CARD2, fg=GOLD, font=(EMOJI_FONT, 52))
weather_icon.pack(side="left", padx=(0, 16))
temp_col = tk.Frame(temp_row, bg=CARD2)
temp_col.pack(side="left")
temp_label = lab(temp_col, "--°", 54, TEXT, True, bg=CARD2)
temp_label.pack(anchor="w")
desc_label = lab(temp_col, "Waiting for data", 13, "#C9D8F5", bg=CARD2)
desc_label.pack(anchor="w")
feels_label = lab(left, "Feels like --°", 10, MUTED, bg=CARD2)
feels_label.pack(anchor="w", pady=(10, 0))

right = tk.Frame(hb, bg=CARD2)
right.grid(row=0, column=1, sticky="nsew", padx=(24, 0))
for c in range(3):
    right.grid_columnconfigure(c, weight=1, uniform="tile")
metric_values = {}
for idx, name in enumerate(["HUMIDITY", "WIND", "PRESSURE", "VISIBILITY", "SUNRISE", "SUNSET"]):
    tile = RoundCard(right, fill=TILE, radius=14, pad=12, outline=TILE, width=10)
    tile.grid(row=idx // 3, column=idx % 3, sticky="nsew", padx=5, pady=5)
    lab(tile.body, name, 8, MUTED, True, bg=TILE).pack(anchor="w")
    value = lab(tile.body, "--", 13, TEXT, True, bg=TILE)
    value.pack(anchor="w", pady=(4, 0))
    metric_values[name] = value

# Forecast
lab(outer, "5-DAY FORECAST", 9, MUTED, True).pack(anchor="w", pady=(2, 8))
forecast_row = tk.Frame(outer, bg=BG)
forecast_row.pack(fill="x")

# Status bar
status_var = tk.StringVar(value="Enter a city and your OpenWeather API key, then press Search.")
status_label = tk.Label(root, textvariable=status_var, bg=BG, fg=MUTED, anchor="w",
                        font=(FONT, 9), padx=26, pady=8, wraplength=1000, justify="left")
status_label.pack(fill="x", side="bottom")


# ---------------------------------------------------------------- rendering
def render_forecast(days, unit_system):
    for child in forecast_row.winfo_children():
        child.destroy()
    temp_unit = unit_symbols(unit_system)[0]
    for i, day in enumerate(days[:5]):
        forecast_row.grid_columnconfigure(i, weight=1, uniform="day")
        card = RoundCard(forecast_row, fill=CARD, radius=18, pad=14, width=10)
        card.grid(row=0, column=i, sticky="nsew", padx=5)
        body = card.body
        weekday = "Today" if i == 0 else day["date"].strftime("%a")
        lab(body, weekday, 10, MUTED, True, bg=CARD).pack()
        tk.Label(body, text=icon_for(day["icon"]), bg=CARD, fg=TEXT,
                 font=(EMOJI_FONT, 26)).pack(pady=(6, 2))
        lab(body, f"{day['high']:.0f}°", 15, TEXT, True, bg=CARD).pack()
        lab(body, f"{day['low']:.0f}{temp_unit}", 10, MUTED, bg=CARD).pack()
        lab(body, f"💧 {day['pop'] * 100:.0f}%", 9, ACCENT_HOVER, bg=CARD).pack(pady=(6, 0))


def render(data):
    global current_place
    current_place = data["place"]
    cur, fc, unit_system = data["current"], data["forecast"], data["units"]
    temp_unit, wind_unit, dist_unit = unit_symbols(unit_system)
    tz = cur.get("timezone", 0)
    weather = cur.get("weather", [{}])[0]
    main = cur.get("main", {})

    location_label.configure(text=current_place["name"])
    time_label.configure(text=local_time(cur["dt"], tz).strftime("%A, %d %B • %H:%M local time"))
    weather_icon.configure(text=icon_for(weather.get("icon", "")))
    temp_label.configure(text=f"{main.get('temp', 0):.0f}{temp_unit}")
    desc_label.configure(text=weather.get("description", "Unavailable").title())
    feels_label.configure(
        text=f"Feels like {main.get('feels_like', 0):.0f}°  •  "
             f"High {main.get('temp_max', 0):.0f}°  •  Low {main.get('temp_min', 0):.0f}°")

    wind = cur.get("wind", {}).get("speed", 0)
    if unit_system == "metric":
        wind *= 3.6  # m/s -> km/h
    visibility = cur.get("visibility", 0) / 1000
    if unit_system == "imperial":
        visibility *= 0.621371
    metric_values["HUMIDITY"].configure(text=f"{main.get('humidity', '--')}%")
    metric_values["WIND"].configure(text=f"{wind:.0f} {wind_unit}")
    metric_values["PRESSURE"].configure(text=f"{main.get('pressure', '--')} hPa")
    metric_values["VISIBILITY"].configure(text=f"{visibility:.1f} {dist_unit}")
    sys_info = cur.get("sys", {})
    for key, field in (("SUNRISE", "sunrise"), ("SUNSET", "sunset")):
        ts = sys_info.get(field)
        metric_values[key].configure(text=local_time(ts, tz).strftime("%H:%M") if ts else "--")

    render_forecast(daily_summary(fc, tz), unit_system)
    status_var.set("Weather updated.")


# ---------------------------------------------------------------- actions
def set_loading(loading):
    search_btn.configure(state="disabled" if loading else "normal",
                         text="Loading…" if loading else "Search")
    unit_btn.configure(state="disabled" if loading else "normal")


def search_weather(reuse_place=False):
    city = city_entry.get().strip()
    key = key_entry.get().strip()
    if not city:
        messagebox.showinfo("Search a city", "Please enter a city name, optionally with a country code.")
        return
    if not key:
        status_var.set("An OpenWeather API key is required. Paste yours into the key field.")
        messagebox.showinfo("API key needed", "Enter your OpenWeather API key to load weather data.")
        return
    set_loading(True)
    status_var.set("Loading weather…")
    place = current_place if reuse_place else None
    threading.Thread(target=worker, args=(city, key, units, place), daemon=True).start()


def toggle_units():
    global units
    units = "imperial" if units == "metric" else "metric"
    unit_btn.configure(text="°F" if units == "imperial" else "°C")
    if current_place:
        search_weather(reuse_place=True)
    persist()


def persist():
    data = {"city": city_entry.get().strip(), "units": units}
    if remember_var.get():
        data["api_key"] = key_entry.get().strip()
    save_config(data)


def poll_results():
    try:
        while True:
            kind, payload = result_queue.get_nowait()
            set_loading(False)
            if kind == "ok":
                render(payload)
                persist()
            else:
                status_var.set(payload)
                messagebox.showerror("Could not load weather", payload)
    except queue.Empty:
        pass
    root.after(100, poll_results)


city_entry.bind("<Return>", lambda e: search_weather())
key_entry.bind("<Return>", lambda e: search_weather())
root.after(100, poll_results)
if key_entry.get().strip():
    root.after(350, search_weather)
root.mainloop()
