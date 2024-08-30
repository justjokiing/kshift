# [kshift](https://github.com/justjokiing/kshift) - KDE Theme Shift

`kshift` is a theme shifting program that integrates with the KDE Plasma desktop environment. The 'theme' includes wallpapers, icon themes, colorschemes, and custom commands. These themes can be run manually by `kshift -t <theme_name>` or by a set time in the `kshift` configuration file. If there is a theme time set, the theme will run automatically through the use of `systemd` timers. Theme times use the same calendar event syntax as systemd timers, but also includes the custom times of `sunrise` and `sunset`. The sunrise and sunset times are determined by the [sunrisesunset.io](https://sunrisesunset.io/) API.

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
      -t {<theme1>,<theme2>}, --theme {<theme1>,<theme2>}
                            Sets the theme
      --install             Installs Kshift
      --remove              Removes Kshift
      -s, --status          Displays kshift timing information

## Installation

#### Required Programs
* KDE Plasma
* Systemd
* Python 3
* Pip

#### Instructions

1. Install colorama, then clone and enter kshift
    ```
    pip install colorama
    git clone https://github.com/justjokiing/kshift
    cd kshift/src
    ```
2. Edit the default variables in the variable file `defaults.yml` or look at usage for command line arguments    
   ```
    # API for getting sun data
    # find yours @ https://sunrisesunset.io/
    # scroll to the bottom of the page, find JSON API link
    sun_api: 'https://api.sunrisesunset.io/json?lat=38.907192&lng=-77.036873'
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
        time: sunrise             # Keywords 'sunrise', 'sunset', or ANY correct systemd 'OnCalendar' time
      night:
        colorscheme: BreezeDark
        icontheme: breeze-dark
        wallpaper: /usr/share/wallpapers/Flow/contents/images_dark/5120x2880.jpg
        command: ''
        time: 
          - sunset
      october:
        wallpaper: /usr/share/wallpapers/FallenLeaf/contents/images/2560x1600.jpg
        time: '*-10-* *:*:*'
        enabled: false            # Disables theme, it will not run on time
   ```
	The themes default are set to a set of default day and night KDE themes and wallpapers. You can add as many themes as you would like at many different times, wallpapers, commands, icons, and colorschemes. None of the theme variables are required. If time is not set, there will be no automatic transition. Each theme's time will be converted to SystemD 'OnCalendar' syntax. The default for 'enabled' is true.
    
    The time variables "sunrise" and "sunset" are keywords to kshift and are replaced with the sunrise and sunset times that your `sun_api` variable sets. Find your api link by going to [sunrisesunset.io](https://sunrisesunset.io/), find your city, then scroll to the bottom to where it says 'JSON API'.

   Make sure to use correct YAML.


3. Create the systemd services and add kshift to local bin
    ```
    ./kshift --install
    ```

    kshift will now be be installed to `~/.local/bin` . Ensure that directory is in `$PATH` if wanted to be manually executed. The kshift timer will be updated after each execution. 

    kshift variables will then be located at `~/.config/kshift/kshift.yml` and follows the same format of `defaults.yml`, any further variable can be done by editing that file or using the `--install` option.

4. Now check to see if the system timers are on and working.
    ```
    ./kshift --status
    ```
    Then test out your themes.
