# kshift - KDE Theme Shift

 kshift is a KDE dark/light shift script that activates at sunrise and sunset when installed. When run manually, it sets the color theme and/or wallpaper to the 'correct' value based on current time. It uses `plasma-apply-colorscheme` for color themes and `plasma-apply-wallpaperimage` for wallpapers.

 During installation, kshift sets systemd timers to run the script at sunrise and sunset.
 If installed and `update_timer` variable is not changed, the timer will update when sunset and sunrise times are updated from the internet.

## Usage

      Usage: kshift OPTIONS [ --install ] [ -h/--help ]

      Sets the system theme to light or dark based on if it is before or after sunrise/sunset
      After sunrise but before sunset (including delays), is set to light mode
      Otherwise, the theme is set to dark mode

        -l  / --location       LOCATION   - sets the location code

        -r  / --sunrise        TIME       - sets default sunrise time
        -s  / --sunset         TIME       - sets default sunset time
        -rd / --risedelay      HOURS      - delay of sunrise day theme change
        -sd / --setdelay       HOURS      - delay of sunset night theme change

        -th / --theme          THEME      - Overrides day and night theme
        -w  / --wallpaper      IMAGE      - Overrides day and night wallpaper

        -n  / --night                     - sets the sunset to current time, making it night.
        -nt / --nightheme      THEME      - theme to be changed to at night
        -nw / --nightwallpaper IMAGE      - wallpaper to be changed to at night

        -d  / --day                       - sets the sunrise to current time, making it day.
        -dt / --daytheme       THEME      - theme to be changed to during the day
        -dw / --daywallpaper   IMAGE      - wallpaper to be changed to during the day

        -t  / --timeout        SECONDS    - network timeout

        -i  / --info                      - Prints status and info of kshift timer and variables
        -h  / --help                      - Prints this message
        --install                         - creates a systemd timer and service for automatic kshift

      The install command will use the current script variables to write a variable file to ~/.kshift.
      Using the other command options will influence the install.


## Demo

This demo is in the day, showing that the default usage will change it to the day theme.

https://user-images.githubusercontent.com/64444712/217895962-ab51fc93-48c3-4edf-b392-2ba4726954e5.mp4


## Installation

1. Clone and enter kshift
    ```
    $ git clone https://github.com/justjokiing/kshift
    $ cd kshift/src
    ```
2. Edit the default variables in the variable file `defaults` or look at usage for command line arguments

| Variable  | Default Values | Useage |
| --------- | -------------- | ------ |
| location | USNY0996 | Location code from https://weather.codes/search |
| sunrise | 6:00 | Sunrise time used when there is no internet |
| sunset | 18:00 | Sunset time used when there is no internet |
| rise_delay | 2 | Number of hours to delay theme change in the morning. This can be negative |
| set_delay | 0 | Number of hours to delay theme change at night. This can be negative |
| dark_theme[^1] | BreezeDark | Theme to be changed to at sunset. |
| light_theme[^1] | BreezeLight | Theme to be changed to at sunrise. |
| day_wallpaper | None | Wallpaper to be switched to during the day |
| night_wallpaper | None | Wallpaper to be switched at night |
| theme | None | Overrides the theme for day and night |
| wallpaper | None | Overrrides the wallpaper for day and night |
| net_timeout | 10 | Number of seconds to wait for internet connection |
| update_timer | 1 | 0 - No kshift timer updates, 1 - timer updates when sun data is gathered. |

[^1]: Themes can be found by `plasma-apply-colorscheme --list-schemes`

3. Create the systemd services and add kshift to local bin
    ```
    $ ./kshift --install [OPTIONS]
    ```

    If you did not edit the `defaults` file, make sure to add command line arguments to change the default values during installation

    kshift will now be be installed to `~/.local/bin` . Ensure that directory is in `$PATH` if wanted to be manually executed.

    kshift variables will then be located at `~/.kshift` and follows the same format of `defaults`, any further variable can be done by editing that file or using the `--install` option.

4. Now check to see if the system timers are on and working.
    ```
    $ ./kshift --info
    ```
