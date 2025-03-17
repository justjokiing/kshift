from datetime import datetime, timedelta
import os
import re
import subprocess
import configparser

from pathlib import Path

from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, Union, List, Tuple, ClassVar


class BaseAttribute(BaseModel):
    """Abstract base class for attribute configurations."""
    val: str

    command: ClassVar[str] = ""

    available: ClassVar[List[str]] = []
    current: ClassVar[Optional[str]] = None

    def apply(self):
        if self.val and self.val != self.current:
            os.system(f"{self.command} '{self.val}'")

    @classmethod
    def fetch_themes(cls, cmd: str,
                     regex: str) -> Tuple[List[str], Optional[str]]:
        """Fetch available and the current theme."""
        if cls.available and cls.current:
            return cls.available, cls.current

        try:
            output = subprocess.run(cmd.split(),
                                    capture_output=True,
                                    text=True,
                                    check=True).stdout.strip()

            for line in output.splitlines():
                match = re.search(regex, line)
                if match:
                    cls.available.append(match.group(1))
                    if "current" in line.lower():
                        cls.current = match.group(1)

            return cls.available, cls.current
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to fetch themes: {e}")

    @classmethod
    def init_themes(cls, fetch_function):
        """Generic initialization for themes."""
        cls.available, cls.current = fetch_function()

    def validate_theme(self):
        if self.val and self.val not in self.available:
            raise ValueError(
                f"Invalid attribute: {self.val}. Available options are {self.available}."
            )

        return self

    def __str__(self) -> str:
        return self.val


class Colorscheme(BaseAttribute):
    available: ClassVar[List[str]] = []
    current: ClassVar[Optional[str]] = None

    command = "plasma-apply-colorscheme"

    @classmethod
    def fetch_colorschemes(cls) -> Tuple[List[str], Optional[str]]:
        """Fetch available colorschemes and the current colorscheme."""
        return cls.fetch_themes(f"{cls.command} -l", r" \* ([\w\s\-]+\w)")

    @model_validator(mode="after")
    def init_colorschemes(self):
        """Initialization of colorscheme variables."""

        self.init_themes(self.fetch_colorschemes)
        return self

    @model_validator(mode="after")
    def validate_colorscheme(self):
        self.validate_theme()
        return self


class CursorTheme(BaseAttribute):
    available: ClassVar[List[str]] = []
    current: ClassVar[Optional[str]] = None

    command = "plasma-apply-cursortheme"

    @classmethod
    def fetch_cursorthemes(cls) -> Tuple[List[str], Optional[str]]:
        """Fetch available cursorthemes and the current cursortheme."""
        return cls.fetch_themes(f"{cls.command} --list-themes",
                                r"\* .* \[(.*?)\]")

    @model_validator(mode="after")
    def init_cursorthemes(self):
        self.init_themes(self.fetch_cursorthemes)
        return self

    @model_validator(mode="after")
    def validate_colorscheme(self):
        self.validate_theme()
        return self


class DesktopTheme(BaseAttribute):
    available: ClassVar[List[str]] = []
    current: ClassVar[Optional[str]] = None

    command = "plasma-apply-desktoptheme"

    @classmethod
    def fetch_desktopthemes(cls) -> Tuple[List[str], Optional[str]]:
        """Fetch available desktopthemes and the current desktoptheme."""
        return cls.fetch_themes(f"{cls.command} --list-themes",
                                r" \* ([\w-]+)")

    @model_validator(mode="after")
    def init_desktopthemes(self):
        self.init_themes(self.fetch_desktopthemes)
        return self

    @model_validator(mode="after")
    def validate_colorscheme(self):
        self.validate_theme()
        return self


class IconTheme(BaseAttribute):
    available: ClassVar[List[str]] = []
    current: ClassVar[Optional[str]] = None

    @classmethod
    def fetch_iconthemes(cls) -> Tuple[List[str], Optional[str]]:
        if cls.available and cls.current:
            return cls.available, cls.current

        home_dir = Path.home()
        old_icon_dir = home_dir / ".icons"
        icon_dir = home_dir / ".local/share/icons"
        system_icon_dir = Path("/usr/share/icons")

        for path in [old_icon_dir, icon_dir, system_icon_dir]:
            if path.exists():
                cls.available += [
                    item.name for item in path.iterdir() if item.is_dir()
                ]

        kdeconfig_path = Path.home() / ".config/kdeglobals"

        if kdeconfig_path.exists():
            config = configparser.ConfigParser()
            config.read(kdeconfig_path)
            cls.current = config.get("Icons", "Theme")

        return cls.available, cls.current

    @model_validator(mode="after")
    def init_iconthemes(self):
        if not self.command:

            search_paths = [
                "/usr/local/libexec", "/usr/local/lib", "/usr/libexec",
                "/usr/lib", "/usr/lib/x86_64-linux-gnu/libexec",
                "/usr/lib/aarch64-linux-gnu/libexec"
            ]

            for path in search_paths:
                executable_path = Path(path) / "plasma-changeicons"
                if executable_path.is_file():
                    IconTheme.command = str(executable_path)

        self.fetch_iconthemes()
        return self

    @model_validator(mode="after")
    def validate_colorscheme(self):
        self.validate_theme()
        return self


class Wallpaper(BaseAttribute):
    path: Optional[Path] = None
    command = "plasma-apply-wallpaperimage"
    available: ClassVar[List[str]] = []
    current: ClassVar[Optional[str]] = None

    @classmethod
    def fetch_wallpapers(cls) -> Tuple[List[str], Optional[str]]:
        if cls.available and cls.current:
            return cls.available, cls.current

        config_file = Path(
            '~/.config/plasma-org.kde.plasma.desktop-appletsrc').expanduser()
        cls.current = ""

        # Open and search for the Image variable
        with open(config_file, 'r') as file:
            section_found = False
            for line in file:
                # Look for the specific section
                if '[Wallpaper][org.kde.image]' in line:
                    section_found = True

                # Look for the Image variable after finding the section
                elif section_found and line.strip().startswith('Image='):
                    cls.current = line.strip().split('=', 1)[1]
                    cls.current = cls.current.replace('file://', '')
                    break

        cls.available = []
        valid_extensions = {
            '.jpg', '.jpeg', '.jxl', '.png', '.bmp', '.webp', '.tiff'
        }

        for d in ["~/.local/share/wallpapers/", "/usr/share/wallpapers"]:
            path = Path(d).expanduser()
            if not path.exists():
                continue

            for entry in path.iterdir():

                if entry.is_dir():  # Check for metadata.json in directories
                    metadata_path = entry / "metadata.json"
                    if metadata_path.is_file():
                        cls.available.append(str(entry))

                elif entry.is_file():  # Check for valid extensions in files
                    if entry.suffix.lower() in valid_extensions:
                        cls.available.append(str(entry))

        return cls.available, cls.current

    @model_validator(mode="after")
    def init_wallpaper(self):
        self.init_themes(self.fetch_wallpapers)

        name_to_path = {Path(p).name: Path(p) for p in self.available}

        if self.val:
            if self.val in name_to_path:
                self.path = name_to_path[self.val]
            else:
                self.path = Path(self.val).expanduser()

        if self.path and self.path.exists():
            self.val = f"'{str(self.path)}'"

            if self.val not in self.available:
                self.available.append(self.val)

        return self

    @model_validator(mode="after")
    def validate_colorscheme(self):
        self.validate_theme()
        return self


class Theme(BaseModel):
    colorscheme: Optional[Colorscheme] = None
    cursortheme: Optional[CursorTheme] = None
    desktoptheme: Optional[DesktopTheme] = None
    icontheme: Optional[IconTheme] = None
    wallpaper: Optional[Wallpaper] = None

    command: Optional[str] = None
    time: List[Union[str, datetime]] = []
    enabled: bool = True

    def __str__(self) -> str:
        components = {}

        for attr in [
                "colorscheme", "cursortheme", "desktoptheme", "icontheme",
                "wallpaper"
        ]:
            if eval(f"self.{attr}"):
                components[attr] = eval(f"self.{attr}.val")

        if self.time:
            time_str = [
                t.strftime("%H:%M") if isinstance(t, datetime) else t
                for t in self.time
            ]
            components["time"] = time_str

        components["enabled"] = self.enabled

        if self.command:
            components["command"] = self.command

        # Format the output like YAML
        result = "\n    ".join(f"{key}: {value}"
                               for key, value in components.items())
        return result

    def kshift(self) -> None:

        for attr in [
                self.colorscheme, self.cursortheme, self.desktoptheme,
                self.icontheme, self.wallpaper
        ]:
            if attr:
                attr.apply()

        if self.command:
            os.system(self.command)

    @model_validator(mode="before")
    def parse_attributes(cls, values):
        mtch = {
            "colorscheme": Colorscheme,
            "cursortheme": CursorTheme,
            "desktoptheme": DesktopTheme,
            "icontheme": IconTheme,
            "wallpaper": Wallpaper
        }

        for attr in mtch.keys():
            if attr in values and isinstance(values[attr], str):
                attr_cls = mtch[attr]
                values[attr] = attr_cls(val=values[attr])

        return values

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
        """HH:MM times are converted to datetime, other strings are to be checked if OnCalendar"""
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
                    "Each time entry must be a string in HH:MM or systemd OnCalendar format."
                )

        return new_times
