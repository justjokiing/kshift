# kshift - KDE Theme Shift

 kshift is a KDE theme shifting script that activates at set times to switch themes, including sunrise and sunset. When run manually, it sets the color theme and/or wallpaper to the 'correct' value based on current time. It uses `plasma-apply-colorscheme` for color themes, `plasma-changeicons` for icon themes, `plasma-apply-wallpaperimage` for wallpapers, and python `os.system()` for commands.

 During installation, kshift sets systemd timers to run the script at any time a theme is set, including sunrise/sunset.
 The sunrise and sunset times are updated when kshift is ran.

## Demo

This demo shows a shift from one theme to another manually, then kshift determining the correct theme to switch to.

https://github.com/justjokiing/kshift/assets/64444712/02e64459-5f5b-477b-a0aa-bdfcd431772d


## Usage

    usage: kshift [-h] [-w WALLPAPER] [-c COLORSCHEME] [-i ICONTHEME] [-t {day,night}] [--install | --remove | -s]

    KDE Theme Switching

    options:
      -h, --help            show this help message and exit
      -w WALLPAPER, --wallpaper WALLPAPER
                            Sets the current wallpaper
      -c COLORSCHEME, --colorscheme COLORSCHEME
                            Sets the colorscheme
      -i ICONTHEME, --icontheme ICONTHEME
                            Sets the icon theme
      -t {day,night}, --theme {day,night}
                            Sets the theme
      --install             Installs Kshift
      --remove              Removes Kshift
      -s, --status          Displays kshift timing information

## Installation

#### Required Programs
* KDE Plasma
* Systemd
* Python 3

#### Instructions

1. Clone and enter kshift
    ```
    $ git clone https://github.com/justjokiing/kshift
    $ cd kshift/src
    ```
2. Edit the default variables in the variable file `defaults.yml` or look at usage for command line arguments    
   ```
    location: USNY0996 # Location Code from https://weather.codes/search
    sunrise: '07:00'   # Default sunrise time, when time data cannot be accessed. These must be in quotes.
    sunset: '19:00'    # Default sunset  time
    rise_delay: 0      # Hour delay for sunrise, can be negative
    set_delay: 0       # Hour delay for sunset
    webdata: true      # Boolean for accessing web for time data
    net_timeout: 10    # How long to wait for network timeout
    themes:
      day:
        colorscheme: BreezeLight  # Check 'plasma-apply-colorscheme -l' for options
        icontheme: breeze
        wallpaper: /usr/share/wallpapers/Flow/contents/images/5120x2880.jpg
        command: ''               # Runs command at theme activation
        time: sunrise             # Keywords 'sunrise', 'sunset', or time in 'HH:MM' format
      night:
        colorscheme: BreezeDark
        icontheme: breeze-dark
        wallpaper: /usr/share/wallpapers/Flow/contents/images_dark/5120x2880.jpg
        command: ''
        time: sunset
   ```
	The themes default are set to a set of default day and night KDE themes and wallpapers. You can add as many themes as you would like at many different times, wallpapers, commands, icons, and colorschemes. None of the theme variables are required. If time is not set, there will be no automatic transition.
    
    The time variables "sunrise" and "sunset" are keywords to kshift and are replaced with the sunrise and sunset times that your location variable sets. __Make sure to use correct YAML syntax.__


3. Create the systemd services and add kshift to local bin
    ```
    $ ./kshift --install
    ```

    kshift will now be be installed to `~/.local/bin` . Ensure that directory is in `$PATH` if wanted to be manually executed. The kshift timer will be updated after each execution. 

    kshift variables will then be located at `~/.kshift.yml` and follows the same format of `defaults.yml`, any further variable can be done by editing that file or using the `--install` option.

4. Now check to see if the system timers are on and working.
    ```
    $ ./kshift --status
    ```
  Then test out your themes.
