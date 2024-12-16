# Import required libraries
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import requests
from datetime import datetime
import urllib3

# Suppress warnings for unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# List of valid country codes mapped to their respective countries
VALID_PHONE_COUNTRY_CODES = {
    "1": "United States/Canada",
    "91": "India",
    "44": "United Kingdom", 
    "86": "China",
    "7": "Russia"
}

# Function to validate the date entered by the user
def validate_date(date):
    """
    Checks if the entered date is valid and within the acceptable range.
    """
    try:
        forecast_date = datetime.strptime(date, "%Y-%m-%d").date()
        today = datetime.today().date()
        max_forecast_date = today.replace(year=today.year + 1)

        if forecast_date < today:
            return "The date cannot be in the past."
        elif forecast_date > max_forecast_date:
            return f"The date is too far in the future. Maximum allowed: {max_forecast_date}."
        return None
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD."

# Function to check if the entered phone country code is valid
def validate_phone_country_code(code):
    """
    Verifies if the phone country code is valid.
    """
    if code not in VALID_PHONE_COUNTRY_CODES:
        return f"Invalid country code: {code}."
    return None

# Function to get latitude and longitude for a given city and country
def get_coordinates(city, country):
    """
    Fetches coordinates (latitude and longitude) for the specified city and country.
    """
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&country={country}"
    response = requests.get(url, verify=False)
    data = response.json()

    if "results" in data and data["results"]:
        location = data["results"][0]
        return location.get("latitude"), location.get("longitude")
    print(f"No results found for city: {city}, country: {country}")
    return None, None

# Function to get weather data from Open-Meteo API
def get_weather_open_meteo(lat, lon, date):
    """
    Fetches weather data for the specified location and date from the Open-Meteo API.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&"
        f"daily=temperature_2m_max,temperature_2m_min,precipitation_sum&"
        f"start_date={date}&end_date={date}&timezone=auto"
    )
    try:
        response = requests.get(url, verify=False)
        data = response.json()

        daily_data = data.get("daily")
        if daily_data:
            return {
                "max_temp": daily_data["temperature_2m_max"][0],
                "min_temp": daily_data["temperature_2m_min"][0],
                "precipitation": daily_data["precipitation_sum"][0],
            }
    except requests.RequestException as e:
        print(f"Error while fetching weather data: {e}")
    return None

# Function to get weather data from OpenWeatherMap API
def get_weather_openweathermap(lat, lon, api_key, date):
    """
    Fetches weather data for the specified location and date from the OpenWeatherMap API.
    """
    url = (
        f"https://api.openweathermap.org/data/2.5/onecall/timemachine?"
        f"lat={lat}&lon={lon}&dt={date}&appid={api_key}&units=metric"
    )
    try:
        response = requests.get(url, verify=False)
        data = response.json()
        current_data = data.get("current", {})

        return {
            "max_temp": current_data.get("temp", None),
            "min_temp": current_data.get("temp", None),
            "precipitation": current_data.get("rain", {}).get("1h", 0),
        }
    except requests.RequestException as e:
        print(f"Error while fetching weather data: {e}")
    return None

# Function to merge weather forecasts from two sources
def calculate_forecast(forecast1, forecast2):
    """
    Combines two weather forecasts by calculating averages for each field.
    """
    def safe_average(value1, value2):
        if value1 is None and value2 is None:
            return 0
        if value1 is None:
            return value2
        if value2 is None:
            return value1
        return (value1 + value2) / 2

    if forecast1 is None:
        return forecast2 or {"max_temp": 0, "min_temp": 0, "precipitation": 0}
    if forecast2 is None:
        return forecast1 or {"max_temp": 0, "min_temp": 0, "precipitation": 0}

    return {
        "max_temp": safe_average(forecast1.get("max_temp"), forecast2.get("max_temp")),
        "min_temp": safe_average(forecast1.get("min_temp"), forecast2.get("min_temp")),
        "precipitation": safe_average(forecast1.get("precipitation"), forecast2.get("precipitation")),
    }

# Function to select the correct weather icon based on precipitation
def get_weather_icon(precipitation):
    """
    Chooses the right weather icon based on the precipitation amount.
    """
    if precipitation == 0:
        icon_path = "sun.png"
    elif 0 < precipitation <= 2:
        icon_path = "cloudy.png"
    elif 2 < precipitation <= 10:
        icon_path = "rain.png"
    else:
        icon_path = "snow.png"

    icon = tk.PhotoImage(file=icon_path)
    resized_icon = icon.subsample(4, 4)
    return resized_icon

# Function to display the weather forecast
def show_forecast():
    """
    Gets the weather forecast and displays it on the screen.
    """
    city = city_entry.get().strip()
    country = country_entry.get().strip()
    date = date_entry.get().strip()

    if not (city and country and date):
        messagebox.showwarning("Input Error", "Provide all inputs: city, country, date.")
        return

    date_error = validate_date(date)
    if date_error:
        messagebox.showerror("Date Error", date_error)
        return

    country_error = validate_phone_country_code(country)
    if country_error:
        messagebox.showerror("Country Code Error", country_error)
        return

    lat, lon = get_coordinates(city, country)
    if lat is None or lon is None:
        messagebox.showerror("Location Error", f"Could not find coordinates for '{city}, {country}'.")
        return

    forecast1 = get_weather_open_meteo(lat, lon, date)
    forecast2 = get_weather_openweathermap(lat, lon, "9db2391360652c6ff7cb0c5f6f974f9b", date)

    forecast = calculate_forecast(forecast1, forecast2)

    if not forecast or (
        forecast.get("max_temp") in (None, 0) and
        forecast.get("min_temp") in (None, 0) and
        forecast.get("precipitation") in (None, 0)
    ):
        forecast_label.config(text="No forecast available.")
        icon_label.config(image="")
        return

    forecast_label.config(text=(f"Forecast for {city} on {date}:\n\n"
                            f"Max Temp: {forecast['max_temp']}°C "
                            f"({round((forecast['max_temp'] * 9 / 5) + 32, 2)}°F)\n\n"
                            f"Min Temp: {forecast['min_temp']}°C "
                            f"({round((forecast['min_temp'] * 9 / 5) + 32, 2)}°F)\n\n"
                            f"Precipitation: {forecast['precipitation']} mm"))


    weather_icon = get_weather_icon(forecast["precipitation"])
    icon_label.config(image=weather_icon)
    icon_label.image = weather_icon

# Set up the GUI
root = tk.Tk()
root.title("Weather Forecast Tool")
root.geometry("500x600")
root.configure(bg="#f0f8ff")

# Title Label
title_label = tk.Label(root, text="Weather Forecast Tool", font=("Helvetica", 16, "bold"), bg="#f0f8ff")
title_label.pack(pady=10)

# Input Frame
input_frame = ttk.Frame(root, padding="10")
input_frame.pack(pady=10)

# Input Fields
ttk.Label(input_frame, text="City:").grid(row=0, column=0, padx=5, pady=5)
city_entry = ttk.Entry(input_frame, width=30)
city_entry.grid(row=0, column=1, padx=5, pady=5)

ttk.Label(input_frame, text="Country (Phone Code):").grid(row=1, column=0, padx=5, pady=5)
country_entry = ttk.Entry(input_frame, width=30)
country_entry.grid(row=1, column=1, padx=5, pady=5)

ttk.Label(input_frame, text="Date (YYYY-MM-DD):").grid(row=2, column=0, padx=5, pady=5)
date_entry = ttk.Entry(input_frame, width=30)
date_entry.grid(row=2, column=1, padx=5, pady=5)

# Forecast Button
forecast_button = ttk.Button(root, text="Get Forecast", command=show_forecast)
forecast_button.pack(pady=10)

# Weather Icon Display
icon_label = tk.Label(root, bg="#f0f8ff")
icon_label.pack(pady=10)

# Weather Forecast Display
forecast_label = tk.Label(root, text="", wraplength=400, justify="left", bg="#f0f8ff", font=("Helvetica", 12))
forecast_label.pack(pady=10)

# Start the application
root.mainloop()
