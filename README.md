# Weather Studio

A modern, dark-themed desktop weather dashboard built with Python and Tkinter. Search any city and get current conditions and a 5-day forecast, powered by the [OpenWeather](https://openweathermap.org/) API.

No third-party packages required: it runs on the Python standard library alone.

<!-- Add a screenshot here once you have one:
![Weather Studio screenshot](docs/screenshot.png)
-->

## Features

- **Current conditions:** temperature, feels-like, daily high/low, and a weather icon with description
- **Detail tiles:** humidity, wind, pressure, visibility, sunrise and sunset (in the searched city's local time)
- **5-day forecast:** one card per day with high/low temperatures and chance of rain
- **Units toggle:** switch between °C / km/h and °F / mph with one click
- **Responsive UI:** API requests run in a background thread, so the window never freezes while loading
- **Modern design:** dark theme with rounded cards and a clean layout
- **Zero dependencies:** only built-in modules (`tkinter`, `urllib`, `json`, and friends)

## Requirements

- Python 3.8 or newer
- Tkinter (included with most Python installers; see the note below for Linux)
- A free OpenWeather API key

## Getting an API key

1. Create a free account at [openweathermap.org](https://home.openweathermap.org/users/sign_up).
2. Open the **API keys** tab in your account.
3. Copy your key.

> New keys can take up to a couple of hours to activate. Until then the app will show a `401` error.

## Installation

```bash
git clone https://github.com/<your-username>/weather-studio.git
cd weather-studio
```

On some Linux distributions Tkinter is a separate package:

```bash
# Debian / Ubuntu
sudo apt install python3-tk
```

## Usage

```bash
python weather_studio.py
```

1. Enter a city, optionally with a country code (for example `Sydney, AU` or `Paris, FR`).
2. Paste your OpenWeather API key into the key field, or set it in the code (see below).
3. Press **Search** or hit **Enter**.
4. Use the **°C / °F** button in the header to switch units.

### Configuring the API key

You can either paste the key into the app each time, or set a default in `weather_studio.py`:

```python
DEFAULT_API_KEY = "your_api_key_here"
```

The **remember** checkbox saves your city, units and (if ticked) your key to `~/.weather_studio.json` in plain text.

> **Security warning:** never commit a real API key to a public repository. Before pushing to GitHub, set `DEFAULT_API_KEY = ""`, and make sure `.weather_studio.json` is never added to the repo. If a key is ever exposed, regenerate it from your OpenWeather account.

## How it works

| Step | OpenWeather endpoint |
| --- | --- |
| City name to coordinates | `/geo/1.0/direct` |
| Current conditions | `/data/2.5/weather` |
| Forecast | `/data/2.5/forecast` |

The free 5-day forecast endpoint returns data in 3-hour steps. The app groups these into one summary per day (highest high, lowest low, peak rain probability, and the icon closest to midday).

## Project structure

```
weather-studio/
├── weather_studio.py   # the entire application
└── README.md
```

## Limitations

- The forecast covers **5 days**, which is the limit of OpenWeather's free plan. A 7-day forecast would require their paid One Call API.
- Emoji weather icons rely on your system's emoji font (Segoe UI Emoji on Windows). Appearance may vary on macOS and Linux.
- Only the best geocoding match is used, so ambiguous city names may need a country code.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `401` error | The key is wrong or not yet active. Check it, or wait for activation. |
| `429` error | Too many requests. Wait a minute and try again. |
| "No matching city found" | Add a country code, e.g. `Cupertino, US`. |
| "Could not connect" | Check your internet connection or firewall. |
| `No module named tkinter` | Install Tkinter (see Installation). |

## Roadmap ideas

- Hourly forecast strip
- Saved favourite cities
- Light theme toggle
- Weather alerts

## Contributing

Issues and pull requests are welcome. For larger changes, please open an issue first to discuss what you would like to change.

## License

Released under the [MIT License](LICENSE). Add a `LICENSE` file to your repository to match.

## Acknowledgements

Weather data provided by [OpenWeather](https://openweathermap.org/).
