# [kshift](https://github.com/justjokiing/kshift): A KDE Plasma Theme Switcher

## Overview

kshift is a dynamic theme manager for KDE Plasma that automatically changes your system's theme (color scheme, icon theme, desktop theme, and wallpaper) based on predefined schedules, times of day, or solar events (e.g., sunrise and sunset). It supports advanced configurations using `systemd` timers, making it a highly customizable solution for KDE Plasma users who want seamless transitions between themes.

## Demo

https://github.com/user-attachments/assets/c18332df-b3b7-4bda-9254-e061a7fa0367

## Why Use kshift?

**Effortless and Dynamic Theme Automation**: Save time by automating theme changes for morning, evening, or specific events without manual adjustments. Coordinate your system's appearance with colorschemes, wallpapers, cursorthemes, icon themes, and desktop themes that match the time of day or occasion.

**Customizable and Reliable Schedules**: Define unique schedules for themes using flexible time settings or solar events like sunrise and sunset. With systemd integration, theme changes are guaranteed to occur on time, even after system reboots.

**Simple and Lightweight**: kshift is built around a straightforward CLI interface and a single YAML configuration file. This design keeps it lightweight and efficient, with no background processes required. By leveraging systemd for scheduling, kshift ensures seamless theme transitions with minimal system resource usage.


## Installation

### Prerequisites

Ensure you have the following installed:

- KDE Plasma
- systemd
- Python 3.7+
- Pip

### Install via `pip`

```bash
pip install kshift
```

### Setup

Run the following command to install kshift's systemd services and timers:

```bash
kshift install
```

This creates necessary configuration and systemd files in your user directory.

## Configuration

kshift uses a YAML configuration file, created during `install` and located at `~/.config/kshift/kshift.yml`. Below is a guide to setting up and customizing your configuration.

Use the command `kshift conf` to open the configuration file in your default editor. Load and confirm this configuration by running `kshift`

### Default Configuration

```yaml
latitude: 39
longitude: -77
sunrise: '08:00'
sunset: '18:00'
rise_delay: 0
set_delay: 0
webdata: true
net_timeout: 10
themes:
  day:
    colorscheme: BreezeLight
    time: sunrise
  night:
    colorscheme: BreezeDark
    time: sunset
```

### Key Configuration Parameters

#### Global Settings

All global parameters are optional; if not provided, they will use the default values as shown in the Default Configuration section above.

| Parameter     | Description                                             |
| ------------- | ------------------------------------------------------- |
| `latitude`    | Latitude coordinate for solar data                      |
| `longitude`   | Longitude coordinate for solar data                     |
| `sunrise`     | Default sunrise time in `HH:MM` format                  |
| `sunset`      | Default sunset time in `HH:MM` format                   |
| `rise_delay`  | Delay sunrise by the specified hours (negative allowed) |
| `set_delay`   | Delay sunset by the specified hours (negative allowed)  |
| `webdata`     | Enable or disable fetching solar data from the web      |
| `net_timeout` | Timeout for fetching solar data in seconds              |

#### Themes

All parameters are optional, but to enable automatic theme switching, a `time` variable must be specified.

| Parameter      | Description                                         | Example Value                     |
| -------------- | --------------------------------------------------- | --------------------------------- |
| `colorscheme`  | Name of the Plasma color scheme                     | `BreezeLight`                     |
| `cursortheme`  | Name of the Plasma cursor theme                     | `HighContrast`                    |
| `desktoptheme` | Name of the Plasma desktop theme                    | `Breeze`                          |
| `icontheme`    | Name of the icon theme                              | `Papirus-Dark`                    |
| `wallpaper`    | Path to the wallpaper image                         | `~/Pictures/morning.jpg`          |
| `command`      | Custom command to execute when the theme is applied | `echo 'Theme applied'`            |
| `time`         | Schedule for theme activation                       | `sunset`, `HH:MM`, `weekly`       |

The `time` variable must either be a sun position (sunrise/sunset), a simple 24HR time (HH:MM), or a string that is a valid `systemd OnCalendar` time. 

If you use a sun position, this will be converted to a 24HR time using the coordinate variables of the configuration.

`OnCalendar` uses a cron-like expression that can represent one or more times in a single expression. More information on this format [here](https://www.freedesktop.org/software/systemd/man/latest/systemd.time.html#Calendar%20Events)

## Usage

### Command-Line Options

Run `kshift` with various options:

- `theme [THEME_NAME]`: Apply a specific theme by name. If no name is provided, kshift determines the appropriate theme to apply based on time and configuration.
    - Positional argument `[THEME_NAME]`: Optional. Specify the theme to apply.
    - `-c, --colorscheme <scheme>`: Apply a specific colorscheme (overrides the theme configuration).
    - `-csr, --cursortheme <theme>`: Apply a specific cursor theme (overrides the theme configuration).
    - `-dk, --desktop_theme <theme>`: Apply a specific desktop theme (overrides the theme configuration).
    - `-i, --icontheme <theme>`: Apply a specific icon theme (overrides the theme configuration).
    - `-w, --wallpaper <path>`: Apply a specific wallpaper (overrides the theme configuration).
- `install`: Install systemd services and timers for kshift.
- `remove`: Remove systemd services and timers for kshift.
- `status`: Display the current status of kshift and active timers.
- `config`: Open the kshift configuration file in the default editor for editing.
- `logs`: View the most recent entries from the kshift log file.
- `list`: List possible themes or attributes

### Examples
| **Command**                                | **Description**                                                  |
|--------------------------------------------|------------------------------------------------------------------|
| `kshift theme night`                       | Apply a theme by name.                                           |
| `kshift`                                   | Have kshift determine the current theme and apply it.            |
| `kshift status`                            | Check current status.                                            |
| `kshift theme night -c BreezeLight -w ~/cat.png` | Apply a theme with modifications.                                 |
| `kshift theme -w ~/cat.png`                | Apply a theme attribute with no theme.                          |
| `kshift list themes`                       | List available kshift themes                                     |
| `kshift list colorschemes`                 | List available colorschemes                                      |


## Systemd Integration

kshift leverages `systemd` timers to provide robust and reliable automation of theme changes. This integration ensures that:

1. **Timely Theme Switching**: Each theme is tied to a `systemd` timer, which allows precise scheduling of theme changes based on time or solar events.
2. **Automatic Startup**: A dedicated startup timer ensures that kshift applies the correct theme when your system boots up.
3. **Flexibility with OnCalendar**: `systemd`'s `OnCalendar` expressions provide flexibility for advanced scheduling. For example, you can schedule themes to activate at exact times, specific days of the week, or even recurring intervals.

### How It Works

- When you install kshift (`kshift install`), it creates a `systemd` service and timer for each theme defined in your configuration.
- The templates used for the services and timers are located in your configuration directory, where if you edit them, their changes will be reflected in the next write.
- The timers are then activated, and `systemd` ensures that the correct theme is applied at the scheduled time.
- The startup timer runs shortly after the system boots, ensuring that kshift applies the most relevant theme based on the current time.

## Uninstallation

To remove kshift, run:

1. `kshift remove` 

    This disables and removes all related systemd timers and services.

2. `pip uninstall kshift`

    Removes the `kshift` package from your computer
