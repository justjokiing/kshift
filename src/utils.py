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
