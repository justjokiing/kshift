import datetime
import os
import yaml
import re
import colorama
import subprocess
import requests

defaults = {
    "location": "USNY0996",
    "sunrise":"08:00",
    "sunset":"19:00",
    "rise_delay": 0,
    "set_delay": 0,
    "net_timeout": 10,
    "webdata": True,
    "themes": { 
        'day': {
            'colorscheme': 'BreezeLight', 
            'wallpaper': '/usr/share/wallpapers/Flow/contents/images/5120x2880.jpg', 
            'time': 'sunrise'
        }, 
        'night': {
            'colorscheme': 'BreezeDark', 
            'wallpaper': '/usr/share/wallpapers/Flow/contents/images_dark/5120x2880.jpg', 
            'time': 'sunset'
        }
    }
}

class config:

    data = {}

    today = datetime.datetime.today().replace(second=0,microsecond=0)

    user = os.getlogin()

    home = os.getenv('HOME')
    if home == None:
        if user == 'root':
            home = "/root"
        else:
            home = '/home/'+user

    kshift_timer_loc= home+"/.config/systemd/user/kshift.timer"
    kshift_service_loc= home+"/.config/systemd/user/kshift.service"

    def __init__(self):

        self.config_loc_base = os.getenv("XDG_CONFIG_HOME")
        if self.config_loc_base is None:
            self.config_loc_base = self.home +'/.config'


        self.config_loc = self.config_loc_base + '/kshift.yml'
        if not os.path.exists(self.config_loc):
            self.data = defaults
            print("No config at: " + self.config_loc+".\nTo change Kshift options, edit 'defaults.yml' and run again with '--install'")
        else:
            config = open(self.config_loc,"r")
            config_data = yaml.safe_load(config)

            for key in defaults.keys():
                try:
                    self.data[key] = config_data[key]
                except KeyError:
                    self.data[key] = defaults[key]


        self.location = self.data["location"]
        location_chk = re.search("^[A-Z]{4}[0-9]{4}$", self.location)
        if type(self.location).__name__ != 'str' or not location_chk:
            raise TypeError("'location' variable is not set correctly. Visit https://weather.codes/ for correct codes.")
        self.tmpfile="/tmp/"+ self.location+ ".out"


        self.sunrise = self.data["sunrise"]
        self.sunset = self.data["sunset"]

        sunrise_chk = re.search("^[0-1]?[0-9]:[0-5][0-9]$", self.sunrise)
        if type(self.sunrise).__name__ != 'str' or not sunrise_chk:
            raise TypeError("'sunrise' variable not set correctly. Use the format HH:MM")
        else:
            sunrise_tmp = datetime.datetime.strptime(self.sunrise, "%H:%M")
            self.sunrise = self.today.replace(hour= sunrise_tmp.hour, minute=sunrise_tmp.minute)

        sunset_chk = re.search("^[0-1]?[0-9]:[0-5][0-9]$", self.sunset)
        if type(self.sunset).__name__ != 'str' or not sunset_chk:
            raise TypeError("'sunset' variable not set correctly. Use the format HH:MM")
        else:
            sunset_tmp = datetime.datetime.strptime(self.sunset, "%H:%M")
            self.sunset = self.today.replace(hour= sunset_tmp.hour, minute=sunset_tmp.minute)


        self.rise_delay = self.data["rise_delay"]
        self.set_delay = self.data["set_delay"]

        if type(self.rise_delay).__name__ != 'int' or self.rise_delay < -23 or self.rise_delay > 23:
            raise TypeError("'rise_delay' variable was not set correctly. Use a number between [-23,23]")
        if type(self.set_delay).__name__ != 'int' or self.set_delay < -23 or self.set_delay > 23:
            raise TypeError("'set_delay' variable was not set correctly. Use a number between [-23,23]")


        self.net_timeout = self.data["net_timeout"]
        if type(self.net_timeout).__name__ != 'int' or self.net_timeout < 0 or self.net_timeout > 60:
            raise TypeError("'net_timeout' variable was not set correctly. Use a number between [0,60]")


        self.webdata = self.data["webdata"]
        if type(self.webdata).__name__ != 'bool':
            raise TypeError("'webdata' variable was not set correctly. Use a boolean value")

    # Adds delay to any times that are "sunset" or "sunrise"
    def delay_time(self, time:datetime.datetime, sun_pos):
        delay = 0
        if sun_pos == "sunrise":
            delay = self.rise_delay
        elif sun_pos == "sunset":
            delay = self.set_delay

        return time.replace(hour=time.hour + delay)

    # Prints the status of Kshift, the timer, and the current config file
    def status(self):
        if os.path.exists(self.kshift_timer_loc) and os.path.exists(self.config_loc):
            timer_status_cmd = "systemctl --user is-enabled kshift.timer"
            timer_status = subprocess.run(timer_status_cmd.split(), stdout=subprocess.PIPE).stdout.decode('utf-8').strip()

            print("##################################")

            if timer_status == "enabled":
                print("Kshift "+colorama.Fore.GREEN + "ENABLED"+colorama.Fore.WHITE +":")
                timer = open(self.kshift_timer_loc, "r")
                for line in timer:
                    m = re.search("[0-9]{1,2}:[0-9]{2}:[0-9]{2}", line)
                    if m:
                        time = m.group(0)
                        print("    Kshift at "+time)

                timer.close()

                print()
            else:
                print("Kshift "+ colorama.Fore.RED+ "DISABLED."+ colorama.Fore.WHITE)


            print("##################################")
            print("kshift local variables @" + self.config_loc)
            print("##################################")

            for line in open(self.config_loc):
                print(line, end='')
        else:
            print("Kshift not installed. Edit 'defaults.yml' and run again with --install")


    # Gets the sundata from the internet and writes it to a tmp file
    #
    # Sets sunrise and sunset
    # Returns the correct sunstate
    def web_sundata(self, sunstate):

        global sunrise
        global sunset

        url = "https://weather.com/weather/today/l/" + self.location
        try:
            data = requests.get(url, timeout=self.net_timeout)
            data = data.text.splitlines()
            for line in data:
                re_sun = re.search("SunriseSunset", line)
                times = re.findall("((1[0-2]|0?[1-9]):([0-5][0-9]) ?([AaPp][Mm]))", line)
                if re_sun and times:
                    sunrise = datetime.datetime.strptime(times[0][0], "%I:%M %p")
                    sunset = datetime.datetime.strptime(times[1][0], "%I:%M %p")

                    sunrise = self.today.replace(hour=sunrise.hour, minute=sunrise.minute)
                    sunset = self.today.replace(hour=sunset.hour, minute=sunset.minute)


            file = open(self.tmpfile, "w")
            file.write(self.location+"\n")
            file.write(sunrise.strftime("%a %b %d %X %Y")+"\n")
            file.write(sunset.strftime("%a %b %d %X %Y"))
        except Exception:
            pass

        if sunstate == "sunrise":
            return sunrise
        elif sunstate == "sunset":
            return sunset
        else:
            raise ValueError

    # Checks to see if sundata is in the designated tmp file, if not, it calls web_sundata
    # Returns the correct sunstate
    def get_sundata(self, sunstate):

        global sunrise
        global sunset

        if os.path.exists(self.tmpfile):
            tmp = open(self.tmpfile,"r")

            last_location = tmp.readline().strip()
            #'Wed Dec  4 20:30:40 2002'
            sunrise_tmp = datetime.datetime.strptime(tmp.readline().strip(),"%a %b %d %X %Y")
            sunset_tmp = datetime.datetime.strptime(tmp.readline().strip(),"%a %b %d %X %Y")

            tmp.close()

            time_distance = self.today - sunrise_tmp
            if time_distance.days >= 1 or last_location != self.location:
                return self.web_sundata(sunstate)
            else:
                sunrise = sunrise_tmp
                sunset = sunset_tmp

                if sunstate == "sunrise":
                    return sunrise
                elif sunstate == "sunset":
                    return sunset
                else:
                    raise ValueError

        else:
            return self.web_sundata(sunstate)
