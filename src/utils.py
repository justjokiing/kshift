import subprocess
import re

# Gets the names of all available colorschemes
def get_colorschemes():

    arr = []

    colorscheme_cmd = "plasma-apply-colorscheme -l"
    output = subprocess.run(colorscheme_cmd.split(), stdout=subprocess.PIPE).stdout.decode('utf-8').strip()

    for line in output.splitlines():
        r = re.search(" \* ([A-Za-z]*)", line)
        if r:
            arr.append(r.group(1))

    return arr

# Gets the current colorscheme
def curr_colorscheme():

    curr = ""

    colorscheme_cmd = "plasma-apply-colorscheme -l"
    output = subprocess.run(colorscheme_cmd.split(), stdout=subprocess.PIPE).stdout.decode('utf-8').strip()

    for line in output.splitlines():
        r = re.search(" \* ([A-Za-z]*) \(current color scheme\)", line)
        if r:
            curr = r.group(1)
            break

    return curr
