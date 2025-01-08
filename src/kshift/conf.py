from datetime import datetime, timedelta
import os
import yaml
import re
import colorama
import subprocess
import requests
import json

from kshift import utils

from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, Optional, Union, List


class ThemeConfig(BaseModel):
    # name: str = Field(description="Name for kshift theme")
    colorscheme: Optional[str] = Field(
        None, description="The name of the color scheme.")
    icontheme: Optional[str] = Field(None,
                                     description="The name of the icon theme.")
    wallpaper: Optional[str] = Field(
        None, description="Path to the wallpaper image.")
    desktoptheme: Optional[str] = Field(None,
                                        description="The desktop theme name.")
    command: Optional[str] = Field(
        None, description="Command to execute when the theme is applied.")
    time: List[Union[str, datetime]] = Field(
        [], description="The time when this theme is applied.")
    enabled: bool = Field(True, description="Whether the theme is enabled.")

    def kshift(self) -> None:

        if self.wallpaper:
            os.system(f"plasma-apply-wallpaperimage {self.wallpaper}")

        if self.colorscheme and self.colorscheme != utils.curr_colorscheme():
            os.system(f"plasma-apply-colorscheme {self.colorscheme}")

        # if self.icontheme and self.icontheme != utils.curr_icontheme():
        if self.icontheme:
            plasma_changeicons = utils.find_plasma_changeicons()
            if (plasma_changeicons is not None):
                os.system(f"{plasma_changeicons} {self.icontheme}")

        if self.desktoptheme and self.desktoptheme != utils.curr_desktoptheme(
        ):
            os.system(f"plasma-apply-desktoptheme {self.desktoptheme}")

        if self.command:
            os.system(self.command)

    @field_validator("colorscheme")
    def validate_colorscheme(cls, value):
        colorschemes = utils.get_colorschemes()
        if value and value not in colorschemes:
            raise ValueError(
                f"Unknown colorscheme: {value}.\nValid options are {colorschemes}"
            )
        else:
            return value

    @field_validator("icontheme")
    def validate_icontheme(cls, value):
        iconthemes = utils.get_iconthemes()
        if value and value not in iconthemes:
            raise ValueError(
                f"Unknown icontheme: {value}.\nValid options are {iconthemes}")
        else:
            return value

    @field_validator("wallpaper")
    def validate_wallpaper(cls, value):
        if value:
            value = Path(value).expanduser()
            if value.exists():
                return value
            else:
                raise ValueError(f"Wallpaper does not exist: {value}")

    @field_validator("desktoptheme")
    def validate_desktoptheme(cls, value):
        desktopthemes = utils.get_desktopthemes()
        if value and value not in desktopthemes:
            raise ValueError(
                f"Unknown desktoptheme: {value}.\nValid options are {desktopthemes}"
            )
        else:
            return value

    @field_validator("time", mode="before")
    def parse_time(cls, value):
        if isinstance(value, str):
            return [value]  # Convert single string to a list
        elif isinstance(value, list):
            if not all(isinstance(item, str) for item in value):
                raise ValueError(
                    "All elements in the 'time' list must be strings.")
            return value
        else:
            raise TypeError("'time' must be a string or a list of strings.")

    @model_validator(mode="after")
    def if_disabled(self):
        if not self.enabled:
            self.time = []

        return self

    @field_validator("time", mode="after")
    def convert_time_strings(cls, times):
        new_times = []
        for item in times:
            if isinstance(item, str):
                if re.match(r'^\d{2}:\d{2}$', item):
                    # Parse "HH:MM" into a datetime object with today's date
                    now = datetime.now()
                    hour, minute = map(int, item.split(':'))
                    dt = now.replace(hour=hour,
                                     minute=minute,
                                     second=0,
                                     microsecond=0)
                    # If the time has already passed today, schedule for tomorrow
                    if dt < now:
                        dt += timedelta(days=1)
                    item = dt

                new_times.append(item)
            elif isinstance(item, datetime):
                new_times.append(item)
            else:
                raise TypeError(
                    "Each time entry must be a string in systemd OnCalendar format."
                )

        return new_times


defaults = {
    "latitude": 39,
    "longitude": -77,
    "sunrise": "08:00",
    "sunset": "18:00",
    "rise_delay": 0,
    "set_delay": 0,
    "net_timeout": 10,
    "themes": {
        'day': ThemeConfig(colorscheme="BreezeLight", time=["sunrise"]),
        'night': ThemeConfig(colorscheme="BreezeDark", time=["sunset"]),
    }
}


class Config(BaseModel):
    # YAML Variables
    latitude: float = Field(
        defaults["latitude"],
        ge=-90,
        le=90,
        description="Latitude coordinate for sun position data")
    longitude: float = Field(
        defaults["longitude"],
        ge=-180,
        le=180,
        description="Longitude Coordinate for sun position data")

    sunrise: datetime = Field(
        datetime.strptime(defaults["sunrise"], "%H:%M"),
        description="Default sunrise time in HH:MM format.")
    sunset: datetime = Field(
        datetime.strptime(defaults["sunset"], "%H:%M"),
        description="Default sunset time in HH:MM format.")
    rise_delay: int = Field(
        defaults["rise_delay"],
        ge=-23,
        le=23,
        description="Hour delay for sunrise, between -23 and 23.")
    set_delay: int = Field(
        defaults["set_delay"],
        ge=-23,
        le=23,
        description="Hour delay for sunset, between -23 and 23.")

    webdata: bool = Field(
        True, description="Whether to fetch sunrise/sunset data from the web.")
    net_timeout: int = Field(
        defaults["net_timeout"],
        ge=0,
        le=60,
        description="Network timeout in seconds, between 0 and 60.")
    themes: Dict[str, ThemeConfig] = Field(defaults["themes"],
                                           description="Dictionary of themes.")

    # Environment-based paths
    home_directory: Path = Field(default=Path.home(),
                                 description="The user's home directory.")
    xdg_config: Path = Field(
        default=Path(os.getenv("XDG_CONFIG_HOME",
                               Path.home() / ".config")),
        description="Base directory for configuration files.",
    )
    xdg_data: Path = Field(
        default=Path(os.getenv("XDG_DATA_HOME",
                               Path.home() / ".local/share")),
        description="Base directory for application data.",
    )
    xdg_cache: Path = Field(
        default=Path(os.getenv("XDG_CACHE_HOME",
                               Path.home() / ".cache")),
        description="Base directory for cache data.",
    )

    # Dependent fields
    systemd_loc: Path = Field(
        Path.home(),
        description="Directory for systemd user timers and services.")
    config_loc_base: Path = Field(
        Path.home(), description="Base configuration directory for kshift.")
    config_loc: Path = Field(
        Path.home(), description="Path to the main kshift configuration file.")
    log_loc: Path = Field(Path.home(), description="Path to kshift log file.")

    sun_api: str = Field("",
                         description="URL to fetch sunrise and sunset data.")
    api_file: Path = Field(
        Path.home(),
        description="Path to the cache file for sunrise and sunset data.")

    @model_validator(mode="after")
    def set_dependant(self):
        # Compute dependent paths
        self.systemd_loc = self.xdg_data / "systemd/user"
        self.config_loc_base = self.xdg_config / "kshift"
        self.config_loc = self.config_loc_base / "kshift.yml"
        self.sun_api = f"https://api.sunrisesunset.io/json?lat={self.latitude}&lng={self.longitude}"
        self.api_file = self.xdg_cache / "kshift" / f"{self.latitude}{self.longitude}.out"

        return self

    @field_validator("sunrise", "sunset", mode="before")
    def validate_time_format(cls, value) -> datetime:
        try:
            value = datetime.strptime(value, "%H:%M")
            value = datetime.combine(datetime.now().date(), value.time())
        except ValueError:
            raise ValueError(
                f"Invalid time format for '{value}'. Use 'HH:MM'.")

        return value

    @model_validator(mode='after')
    def parse_sun_times(self):

        def apply_delay(time_obj: datetime, delay_hours: int) -> datetime:
            return time_obj + timedelta(hours=delay_hours)

        for name, config in self.themes.items():

            updated_times = []
            for t in config.time:
                if isinstance(t, str):
                    if t == "sunrise":
                        t = apply_delay(self.get_sundata(t), self.rise_delay)
                    elif t == "sunset":
                        t = apply_delay(self.get_sundata(t), self.set_delay)
                    else:
                        t = utils.time_to_systemd(t)

                    updated_times.append(t)
                elif isinstance(t, datetime):
                    updated_times.append(t)
                else:
                    raise ValueError(
                        f"Unsupported time in theme '{name}': {t}")

            # Update the theme's time with resolved datetime objects
            config.time = updated_times

        return self

    # Prints the status of Kshift, the timer, and the current config file
    def status(self):
        if self.systemd_loc.exists() and self.config_loc.exists():

            timer_status_cmd = "systemctl --user is-enabled "
            enabled = False
            timed_outputs = ""

            for f in os.listdir(self.systemd_loc):
                if 'kshift-' in f and '.timer' in f:
                    timer_status = subprocess.run(
                        (timer_status_cmd + f).split(),
                        stdout=subprocess.PIPE).stdout.decode('utf-8').strip()

                    if timer_status == "enabled":
                        enabled = True

                        theme_name = f.replace(".timer", "").split("-")[1]

                        timer = open(self.systemd_loc / f, "r")
                        for line in timer:
                            m = re.search("OnCalendar=(.*)", line)
                            if m:
                                time = m.group(1)
                                timed_outputs += f"{theme_name:<10} {time}\n"

                        timer.close()

            if enabled:
                print("kshift status: " + colorama.Fore.GREEN + "ENABLED" +
                      colorama.Fore.WHITE)
                print(timed_outputs, end='')
            else:
                print("kshift status: " + colorama.Fore.RED + "DISABLED." +
                      colorama.Fore.WHITE)
        else:
            print(
                "kshift not installed. Run again with `--install` and edit your config with `--config`"
            )

    def _select_sunstate(self, sunstate) -> datetime:
        if sunstate == "sunrise":
            return self.sunrise
        elif sunstate == "sunset":
            return self.sunset
        else:
            raise ValueError(
                f"Invalid sunstate '{sunstate}'. Use 'sunrise' or 'sunset'.")

    # Gets the sundata from the internet and writes it to a tmp file
    #
    # Sets sunrise and sunset
    # Returns the correct sunstate
    def web_sundata(self, sunstate):
        url = self.sun_api
        try:
            response = requests.get(url, timeout=self.net_timeout)
            response.raise_for_status()
            data = response.json()

            sunrise = datetime.strptime(data["results"]["sunrise"],
                                        "%I:%M:%S %p").time()
            sunset = datetime.strptime(data["results"]["sunset"],
                                       "%I:%M:%S %p").time()

            self.sunrise = datetime.combine(datetime.now().date(), sunrise)
            self.sunset = datetime.combine(datetime.now().date(), sunset)

            cache_data = {
                "location": f"{self.latitude},{self.longitude}",
                "sunrise": self.sunrise.isoformat(),
                "sunset": self.sunset.isoformat()
            }

            cache_dir = self.api_file.parent
            cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.api_file, "w") as file:
                json.dump(cache_data, file)

        except requests.exceptions.ConnectionError as e:
            print(
                f"Connection error: {e}. Could not connect to {url}. Falling back to defaults."
            )
        except requests.exceptions.Timeout as e:
            print(
                f"Timeout error: {e}. The request to {url} took too long. Falling back to defaults."
            )
        except requests.exceptions.HTTPError as e:
            print(
                f"HTTP error: {e}. Invalid response from the server. Falling back to defaults."
            )
        except json.JSONDecodeError as e:
            print(
                f"JSON decoding error: {e}. Invalid response format. Falling back to defaults."
            )
        except Exception as e:
            print(f"Unexpected error: {e}. Falling back to defaults.")

        return self._select_sunstate(sunstate)

    # Checks to see if sundata is in the designated tmp file, if not, it calls web_sundata
    # Returns the correct sunstate
    def get_sundata(self, sunstate):
        if self.webdata is False:
            return self._select_sunstate(sunstate)

        elif self.api_file.exists():
            try:
                with open(self.api_file, "r") as file:
                    cache_data = json.load(file)
                    cache_data["sunrise"] = datetime.fromisoformat(
                        cache_data["sunrise"])
                    cache_data["sunset"] = datetime.fromisoformat(
                        cache_data["sunset"])

                if cache_data[
                        "location"] == f"{self.latitude},{self.longitude}":

                    self.sunrise = datetime.combine(
                        datetime.now().date(), cache_data["sunrise"].time())
                    self.sunset = datetime.combine(datetime.now().date(),
                                                   cache_data["sunset"].time())

                if cache_data["sunrise"].date() == datetime.today().date(
                ) and cache_data["sunset"].date() == datetime.today().date():
                    return self._select_sunstate(sunstate)

            except (ValueError, IndexError):
                pass  # Fall back to fetching data if the cache is corrupted

        # Fetch fresh data if the cache is invalid or missing
        return self.web_sundata(sunstate)


def load_config() -> Config:
    # Determine the config file path
    config_base = Path.home() / ".config/kshift"
    config_file = config_base / "kshift.yml"

    config_data = defaults

    # If user configuration exists, overwrite the defaults
    if config_file.exists():
        with open(config_file, "r") as file:
            try:
                user_data = yaml.safe_load(file)
                config_data.update(user_data)  # Merge user data into defaults
            except yaml.YAMLError as e:
                print(f"Error reading kshift.yml: {e}")
                raise
    else:
        print(
            f"User configuration file not found at {config_file}. Using defaults."
        )

    # Instantiate and return the Config object
    return Config(**config_data)
