import os
import datetime

from functools import total_ordering

import conf
import utils

c = conf.config()

# Class used for holding a theme data, and sorting these themes

@total_ordering
class Theme:
    attributes = ["colorscheme", "icontheme", "wallpaper", "command", "time", "enabled"]

    colorschemes = utils.get_colorschemes()
    iconthemes = utils.get_iconthemes()

    def __init__(self, name, colorscheme, icontheme, wallpaper, command, time, enabled):
        self.name = name

        if colorscheme is None or self.colorschemes.count(colorscheme) >= 1:
            self.colorscheme = colorscheme
        else:
            raise ValueError(f"Unknown colorscheme: {colorscheme}")

        if icontheme is None or self.iconthemes.count(icontheme) >= 1:
            self.icontheme = icontheme
        else:
            raise ValueError(f"Unknown icon theme: {icontheme}")

        if wallpaper is None or os.path.exists(wallpaper):
            self.wallpaper = wallpaper
        else:
            raise ValueError(f"Wallpaper does not exist: {wallpaper}")

        self.command = command

        if time == "sunrise" or time == "sunset":
            if c.webdata:
                time = c.delay_time(c.get_sundata(time), time)
            else:
                # Get default sunrise/sunset time if no webdata
                tmp_time = datetime.datetime.strptime(c.data[time], "%H:%M")
                time = c.delay_time(c.today.replace(hour=tmp_time.hour, minute=tmp_time.minute), time)

        # A disabled theme just gets no time
        # allows you to still call it
        if enabled is False:
            time = None

        self.time = utils.time_to_systemd(time)

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o,Theme) and self.name == __o.name and self.time == __o.time

    def __ge__(self, __o) -> bool:
        if isinstance(__o,Theme) and __o.time is not None and self.time is not None:
            return utils.systemd_to_datetime(self.time, c.today) > utils.systemd_to_datetime(__o.time, c.today)
        else:
            return False

    def __le__(self, __o) -> bool:
        if isinstance(__o,Theme) and __o.time is not None and self.time is not None:
            return utils.systemd_to_datetime(self.time, c.today) < utils.systemd_to_datetime(__o.time, c.today)
        else:
            return False

    def __repr__(self) -> str:
        return f"Name: {self.name}, ColorScheme: {self.colorscheme}, IconTheme: {self.icontheme}, Wallpaper: {self.wallpaper}, Time: {self.time}\n"


    ###################################
    # Kshift
    ###################################


    # This is where the magic happens
    # Just uses a theme's vars to set the colorscheme and wallpaper, and run any command
    def kshift(self):

        if self.wallpaper:
            os.system(f"plasma-apply-wallpaperimage {self.wallpaper}")

        if self.colorscheme and self.colorscheme != utils.curr_colorscheme():
            os.system(f"plasma-apply-colorscheme {self.colorscheme}")

        if self.icontheme and self.icontheme != utils.curr_icontheme():
            plasma_changeicons = utils.find_plasma_changeicons()
            if (plasma_changeicons is not None):
                os.system(f"{plasma_changeicons} {self.icontheme}")

        if self.command:
            os.system(self.command)
