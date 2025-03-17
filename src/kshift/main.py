#!/usr/bin/env python

import click

from datetime import datetime
from os import system, makedirs, getenv
from re import search
import subprocess
from shutil import which

import logging
from logging.handlers import RotatingFileHandler
import json

from importlib.resources import files

from kshift.conf import load_config

from string import Template

from kshift.theme import *

c = load_config()

###################################
# Logging
###################################

log_file = c.xdg_cache / "kshift" / "kshift.log"
cache_dir = log_file.parent
cache_dir.mkdir(parents=True, exist_ok=True)

# Setup RotatingFileHandler for the same file
handler = RotatingFileHandler(log_file,
                              maxBytes=1 * 1024 * 1024,
                              backupCount=1)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s",
                              datefmt="%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)

# Configure logging
logging.basicConfig(level=logging.INFO, handlers=[handler])


def log_theme_change(theme_name):
    """
    Log a theme change event with structured data.
    """
    log_data = {
        "event": "theme_change",
        "theme": theme_name,
        "source": getenv("SOURCE", "direct")
    }
    logging.info(json.dumps(log_data))  # Use JSON for structured logs


def log_element_change(theme: Theme):
    log_data = {"event": "specific_change", "theme": str(theme)}
    logging.info(json.dumps(log_data))


def log_timer_write(themes):
    log_data = {"event": "timers_written", "themes": themes}
    logging.info(json.dumps(log_data))


def parse_theme_logs(log_file, reference_time=None):
    """
    Parse the log file to determine the last activated theme.
    """

    last_theme = None
    reference_time = reference_time or datetime.now()

    with open(log_file, "r") as f:
        # for line in f:
        for line in reversed(f.readlines()):
            try:
                # Extract JSON from log message
                timestamp, _, json_data = line.partition("- INFO - ")
                log_entry = json.loads(json_data)

                # Check if this log entry is a theme change event
                if log_entry.get("event") == "theme_change" and log_entry.get(
                        "source") == "systemd" and c.themes.get(
                            log_entry.get("theme")):

                    log_time = datetime.fromisoformat(timestamp)
                    return (log_entry["theme"], log_time)

            except (json.JSONDecodeError, ValueError):
                # Skip lines that aren't properly formatted
                continue

    return last_theme


###################################
# systemd
###################################


# Writes the timers/services for each timed theme
def write_systemd():

    def write_timer(path, subs):
        # write theme timer
        with open(path, "w") as file:
            template = Template(
                open(c.config_loc_base / "templates/template.timer").read())

            file.write(template.substitute(subs))

    def write_service(path, subs):
        # write theme timer
        with open(path, "w") as file:
            template = Template(
                open(c.config_loc_base / "templates/template.service").read())

            file.write(template.substitute(subs))

    kshift_path = which("kshift") or "kshift"
    written_timers = []

    # Remove any old timers
    for name, conf in c.themes.items():
        timer = c.systemd_loc / f"kshift-{name}.timer"
        if not conf.time and timer.exists():
            timer.unlink()

    # Write services for each theme
    # Write timer if they have 'time' option
    for (name, conf) in c.themes.items():

        theme_service_str = " ".join([
            f'kshift-{x[0]}.service' for x in c.themes.items()
            if x[0] is not name
        ])

        # Convert any datetime objects to simple HH:MM
        # Datetime objects were originally in HH:MM or sunset/sunrise
        # If it is a string, it was a verified OnCalendar time
        theme_times = []
        for t in conf.time:
            if isinstance(t, datetime):
                t = datetime.strftime(t, "%H:%M")

            theme_times.append(t)

        # Extract old timer times to check if the timer needs to be updated
        timer_path = (c.systemd_loc / f"kshift-{name}.timer")
        timer_times = []

        timer_changed = False
        if timer_path.exists():

            for line in open(timer_path, "r"):
                r = search("OnCalendar=(.*)\n", line)
                if r:
                    timer_times.append(r.group(1))

            timer_changed = timer_times != theme_times

        if not timer_path.exists() or timer_changed:

            calendar_times = ""
            for t in theme_times:
                calendar_times += f'OnCalendar={t}\n'

            # Cannot have timer with no timer action
            if calendar_times:
                subs = {
                    "description": f'kshift timer for theme {name}',
                    "unit_options": f'After={theme_service_str}',
                    "timer_action": f'{calendar_times}\nPersistent=true'
                }
                write_timer(timer_path, subs)
                written_timers.append(name)

            subs = {
                "description": f'kshift service for theme {name}',
                "command": f"{kshift_path} theme {name}"
            }
            write_service(c.systemd_loc / f"kshift-{name}.service", subs)

    # write startup timer & service
    startup_timer = c.systemd_loc / "kshift-startup.timer"
    startup_service = c.systemd_loc / "kshift-startup.service"
    if not startup_timer.exists() or not startup_service.exists():

        subs = {
            "description": 'kshift startup timer',
            "unit_options": "",
            "timer_action": 'OnStartupSec=5'
        }
        write_timer(startup_timer, subs)
        written_timers.append("startup")

        subs = {
            "description": 'kshift startup service',
            "command": f"{kshift_path}"
        }
        write_service(startup_service, subs)

    if len(written_timers) > 0:
        log_timer_write(written_timers)

        timers_str = ""
        for t in written_timers:
            timers_str += f"kshift-{t}.timer "

        system("systemctl --user daemon-reload")
        system(f"systemctl --user enable { timers_str }")
        system(f"systemctl --user start { timers_str }")


###################################
# CLI
###################################


@click.group(
    invoke_without_command=True,
    help="KDE Theme Switching (kshift)",
)
@click.pass_context
def cli(ctx):
    """Main entry point for the kshift CLI."""
    if ctx.invoked_subcommand is None:
        # Call the theme subcommand if no subcommand is provided
        ctx.invoke(theme)


# Installs systemd services and timers
@cli.command(help="Install kshift systemd services")
def install():

    answer = input("Are you sure you want to install kshift? [y/n]: ")
    if answer in ("Y", "y", "yes"):

        if not c.config_loc_base.exists():
            c.config_loc_base.mkdir()

        if not (c.config_loc_base / "templates").exists():
            system(
                f'cp -r {files("kshift") / "templates"} {c.config_loc_base}')

        if not c.config_loc.exists():
            system(
                f"cp {files('kshift') / 'defaults.yml'} {c.config_loc_base / 'kshift.yml'}"
            )

        makedirs(c.systemd_loc, exist_ok=True)

        print("Writing & enabling theme timers and services...")
        write_systemd()


# Removes kshift timer
@cli.command(help="Remove kshift systemd services")
def remove():

    answer = input("Are you sure you want to remove kshift? [y/n]: ")
    if answer in ("Y", "y", "yes"):
        print("Removing kshift timers and services...")

        system(f"rm {c.systemd_loc / 'kshift-'}*")

        system("systemctl --user daemon-reload")


@cli.command(help="Display kshift status")
def status():
    c.status()


@cli.command(help="Edit the kshift configuration file")
def config():
    """Edit the configuration file."""

    filepath = c.config_loc
    if filepath.exists():
        try:
            # Use xdg-open to open the file in the default editor
            subprocess.run(["xdg-open", filepath], check=True)
            print(f"Opened {filepath} in the default editor.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to open the file: {e}")
    else:
        print(f"Config does not exist @ {filepath}")


@cli.command(help="Tail on kshift logs")
@click.option(
    "-a",
    "--all",
    is_flag=True,
    help="Print the entire log file",
)
def logs(all):

    print(f"Log @ {log_file}")
    with open(log_file, 'r') as f:
        lines = f.readlines()
        if not all:
            lines = lines[-10:]

        for line in lines:
            print(line, end="")


@cli.command(help="List possible themes or attributes")
@click.argument("attribute",
                type=click.Choice([
                    "themes", "colorschemes", "cursorthemes", "desktopthemes",
                    "iconthemes", "wallpapers"
                ],
                                  case_sensitive=False))
def list(attribute):

    def print_available(attr, items):
        print(f"Available {attr}:")
        for a in items:
            print(f"- {a}")

    if attribute == "themes":
        for name, conf in c.themes.items():
            print(f"theme: {name}\n    {conf}\n")
            pass

    items = []
    match attribute:
    # items are the class.available
        case "colorschemes":
            items = Colorscheme.fetch_colorschemes()[0]
        case "cursorthemes":
            items = CursorTheme.fetch_cursorthemes()[0]
        case "desktopthemes":
            items = DesktopTheme.fetch_desktopthemes()[0]
        case "iconthemes":
            items = IconTheme.fetch_iconthemes()[0]
        case "wallpapers":
            items = Wallpaper.fetch_wallpapers()[0]

    if items:
        print_available(attribute, items)


@cli.command(help="Change themes or apply specific theme elements")
@click.argument("theme",
                type=str,
                required=False,
                default=None,
                nargs=1,
                metavar="[THEME_NAME]")
@click.option(
    "-csr",
    "--cursortheme",
    type=str,
    help="Set a specific cursor theme (overrides theme)",
)
@click.option(
    "-c",
    "--colorscheme",
    type=str,
    help="Set a specific colorscheme (overrides theme)",
)
@click.option(
    "-dk",
    "--desktop_theme",
    type=str,
    help="Set a specific desktop theme (overrides theme)",
)
@click.option(
    "-i",
    "--icontheme",
    type=str,
    help="Set a specific icon theme (overrides theme)",
)
@click.option(
    "-w",
    "--wallpaper",
    type=str,
    help="Set a specific wallpaper (overrides theme)",
)
@click.option(
    "-dk",
    "--desktop_theme",
    type=str,
    help="Set a specific desktop theme (overrides theme)",
)
def theme(theme, colorscheme, cursortheme, desktop_theme, icontheme,
          wallpaper):

    kshift_status = subprocess.run(
        "systemctl --user is-enabled kshift-startup.timer".split(),
        stdout=subprocess.PIPE).stdout.decode('utf-8').strip()

    if theme:
        if theme in c.themes:
            print(f"Applying theme {theme}...")
            c.themes[theme].kshift()
            log_theme_change(theme)
        else:
            print(f"Error: Theme '{theme}' not found in configuration.")

    if any([colorscheme, cursortheme, desktop_theme, icontheme, wallpaper]):
        # Apply individual theme elements dynamically
        custom_theme = Theme(
            colorscheme=colorscheme,
            cursortheme=cursortheme,
            icontheme=icontheme,
            wallpaper=wallpaper,
            desktoptheme=desktop_theme,
        )
        print("Applying custom theme elements...")
        custom_theme.kshift()
        log_element_change(custom_theme)

    # If there were no arguments
    # Determine which theme should be active, then shift to it
    if not any([theme, colorscheme, icontheme, wallpaper, desktop_theme]):

        themes = []

        # Add each theme with simple timer, ie not strict OnCalendar time
        for name, conf in c.themes.items():
            for t in conf.time:
                if isinstance(t, datetime) and datetime.now() >= t:
                    themes.append((name, t))

        # The last theme activated by timer could be correct active theme
        # Find this last time only if kshift is enabled in systemd
        if kshift_status == "enabled":
            last_log_theme = parse_theme_logs(log_file)
            if last_log_theme:
                themes.append(last_log_theme)

        # Sort themes such that the one closest to present is last
        # Then change to this theme
        themes = sorted(themes, key=lambda x: x[1])
        if themes:
            curr_theme = themes[-1][0]
            print(f"Applying theme {curr_theme}...")

            c.themes[curr_theme].kshift()
            log_theme_change(curr_theme)

    # Update systemd if installed
    if kshift_status == "enabled":
        write_systemd()


if __name__ == "__main__":
    cli()
