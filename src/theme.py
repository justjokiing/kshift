import os
import datetime

from functools import total_ordering

import conf
import utils

c = conf.config();

# Class used for holding a theme data, and sorting these themes

@total_ordering
class Theme:
    attributes = ["colorscheme", "wallpaper", "command", "time"]

    colorschemes = utils.get_colorschemes()

    def __init__(self, name, colorscheme, wallpaper, command, time):
        self.name = name

        if colorscheme == None or self.colorschemes.count(colorscheme) >= 1:
            self.colorscheme = colorscheme
        else:
            raise ValueError("Unknown colorscheme: "+colorscheme)


        if wallpaper == None or os.path.exists(wallpaper):
            self.wallpaper = wallpaper
        else:
            raise ValueError("Wallpaper does not exist: "+wallpaper)

        self.command = command


        if time == "sunrise" or time == "sunset":
            if c.webdata:
                self.time = c.delay_time(c.get_sundata(time), time)
            else:
                tmp_time = datetime.datetime.strptime(c.data[time], "%H:%M")
                self.time = c.delay_time(c.today.replace(hour=tmp_time.hour, minute=tmp_time.minute), time)
        elif time == None:
            self.time = None
        else:
            tmp_time = datetime.datetime.strptime(time, "%H:%M")
            self.time = c.today.replace(hour=tmp_time.hour, minute=tmp_time.minute)

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o,Theme) and self.name == __o.name

    def __ge__(self, __o) -> bool:
        if isinstance(__o,Theme) and __o.time != None and self.time != None:
            return self.time > __o.time
        else:
            return False

    def __le__(self, __o) -> bool:
        if isinstance(__o,Theme) and __o.time != None and self.time != None:
            return self.time < __o.time
        else:
            return False

    def __repr__(self) -> str:
        return "Name: {}, ColorScheme: {}, Wallpaper: {}, Time: {}\n".format(self.name,self.colorscheme,self.wallpaper,self.time)


    ###################################
    # Kshift
    ###################################


    # This is where the magic happens
    # Just uses a theme's vars to set the colorscheme and wallpaper, and run any command
    def kshift(self):

        if self.wallpaper:
            os.system("plasma-apply-wallpaperimage "+ self.wallpaper)

        if self.colorscheme and self.colorscheme != utils.curr_colorscheme():
            os.system("plasma-apply-colorscheme "+ self.colorscheme)

        if self.command:
            os.system(self.command)

