from datetime import datetime
import subprocess
import re
import os
import configparser

# Gets the names of all available colorschemes
def get_colorschemes():

    arr = []

    colorscheme_cmd = "plasma-apply-colorscheme -l"
    output = subprocess.run(colorscheme_cmd.split(), stdout=subprocess.PIPE).stdout.decode('utf-8').strip()

    for line in output.splitlines():
        r = re.search(" \\* ([A-Za-z]*)", line)
        if r:
            arr.append(r.group(1))

    return arr

# Gets the current colorscheme
def curr_colorscheme():

    curr = ""

    colorscheme_cmd = "plasma-apply-colorscheme -l"
    output = subprocess.run(colorscheme_cmd.split(), stdout=subprocess.PIPE).stdout.decode('utf-8').strip()

    for line in output.splitlines():
        r = re.search(" \\* ([A-Za-z]*) \\(current color scheme\\)", line)
        if r:
            curr = r.group(1)
            break

    return curr

def get_iconthemes():

    arr = []

    home_dir = os.path.expanduser("~")
    old_icon_dir = home_dir + "/.icons"
    icon_dir = home_dir + "/.local/share/icons"
    system_icon_dir = "/usr/share/icons"

    for path in [old_icon_dir, icon_dir, system_icon_dir]:
        if os.path.exists(path):
            output = subprocess.run(["ls", path], stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
            arr += output.split()

    return arr

# Gets the current icon theme
def curr_icontheme():

    curr = ""
    kdeconfig_path = os.path.expanduser("~") + "/.config/kdeglobals"

    if os.path.exists(kdeconfig_path):
        config = configparser.ConfigParser()
        config.read(kdeconfig_path)
        curr = config["Icons"]["Theme"]

    return curr


# Gets the path to plasma-changeicon
def find_plasma_changeicons():
    search_paths = [
        "/usr/local/libexec",
        "/usr/local/lib",
        "/usr/libexec",
        "/usr/lib",
        "/usr/lib/x86_64-linux-gnu/libexec",
        "/usr/lib/aarch64-linux-gnu/libexec"
    ]

    for path in search_paths:
        executable_path = os.path.join(path, "plasma-changeicons")
        if os.path.isfile(executable_path):
            return executable_path

    return None

def time_to_systemd(time):

    if time is None:
        return time

    command = "systemd-analyze calendar "+time
    process = subprocess.run(command.split(), stdout=subprocess.PIPE)
    stat_code = process.returncode

    if stat_code == 0:
        calendar_time = ""
        output = process.stdout.decode('utf-8').strip()

        for line in output.splitlines():
            r = re.search("Normalized form: (.*)", line)
            if r:
                calendar_time = r.group(1)
                break

        return calendar_time

    else:
        raise Exception("Invalid SystemD calendar time!: "+time )


# Converting to today's version of datetime for theme comparison
def systemd_to_datetime(time, today: datetime) -> datetime:

    if time is None or type(time).__name__ == "datetime":
        return time

    parts = time.split()

    # Y-M-D HH:MM:SS
    # OR
    # DOW Y-M-D HH:MM:SS

    if len(parts) == 3:
        dow = parts[0]
        time = " ".join(parts[1:])

    r = re.search("(.*)-(.*)-(.*) (.*):(.*):(.*)", time)

    today_broken = [ today.year, today.month, today.day, today.hour, today.minute, today.second ]
    final = []

    for i in range(6):
        final.append( r.group(i+1) if r.group(i+1) != '*' else today_broken[i] )

    if len(parts) == 3:
        new_time = "{} {}-{}-{} {}:{}:{}".format(dow, *final)

        date = datetime.strptime(new_time, "%a %Y-%m-%d %H:%M:%S")
    else:
        new_time = "{}-{}-{} {}:{}:{}".format(*final)

        date = datetime.strptime(new_time, "%Y-%m-%d %H:%M:%S")

    return date


