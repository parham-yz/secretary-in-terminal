#!/usr/bin/env python3
import curses
import re
import sys
import argparse
import time
import os
from datetime import datetime, date, time as dtime, timedelta

def parse_plan_file(filename):
    """
    Parse a plan file and return a list of day schedules.

    Each day schedule is a dict containing:
       - 'date': a datetime.date object,
       - 'header': the header text (e.g. "Monday, April 7th, 2025 - No Gym"),
       - 'events': a list of events, where each event is a dict with:
            'start': datetime.datetime,
            'end': datetime.datetime,
            'description': string
    """
    with open(filename, "r") as f:
        lines = f.readlines()
    
    days = []  # list to hold each day's schedule
    current_day = None
    current_events = []
    
    # Pattern for a day header line, e.g. "Monday, April 7th, 2025 - No Gym"
    day_header_pattern = re.compile(r"^([A-Za-z]+),\s+([A-Za-z]+)\s+(\d{1,2}(?:st|nd|rd|th)?),\s+(\d{4}).*")
    # Pattern for schedule events, e.g. "9:00 AM → 10:15 AM: Task details"
    event_pattern = re.compile(r"^(\d{1,2}:\d{2}\s*(?:AM|PM))\s*→\s*(\d{1,2}:\d{2}\s*(?:AM|PM)):\s*(.+)$")
    
    for line in lines:
        line = line.strip()
        if line == "":
            continue
        # Check for a day header
        day_header_match = day_header_pattern.match(line)
        if day_header_match:
            # If there is an existing day block, finalize it.
            if current_day is not None:
                current_day["events"] = current_events
                days.append(current_day)
                current_events = []
            # Parse the header
            weekday_str = day_header_match.group(1)
            month_str = day_header_match.group(2)
            day_str_with_suffix = day_header_match.group(3)
            year_str = day_header_match.group(4)
            # Remove ordinal suffix ("st", "nd", "rd", "th")
            day_str = re.sub(r"(st|nd|rd|th)", "", day_str_with_suffix)
            try:
                day_date = datetime.strptime(f"{month_str} {day_str} {year_str}", "%B %d %Y").date()
            except ValueError:
                day_date = None
            header = line  # retained in the data but not displayed in the UI
            current_day = {"date": day_date, "header": header, "events": []}
        else:
            # Check if the line describes a scheduled event.
            event_match = event_pattern.match(line)
            if event_match and current_day is not None:
                start_str = event_match.group(1)
                end_str = event_match.group(2)
                description = event_match.group(3)
                try:
                    start_time_obj = datetime.strptime(start_str.strip(), "%I:%M %p").time()
                    end_time_obj = datetime.strptime(end_str.strip(), "%I:%M %p").time()
                except Exception:
                    continue
                # Combine the parsed time with the current day's date
                start_dt = datetime.combine(current_day["date"], start_time_obj)
                end_dt = datetime.combine(current_day["date"], end_time_obj)
                event = {"start": start_dt, "end": end_dt, "description": description}
                current_events.append(event)
    
    # Append the last day's schedule (if any)
    if current_day is not None:
        current_day["events"] = current_events
        days.append(current_day)
    return days

def find_today_schedule(days, target_date):
    """Return the schedule for the target_date if available."""
    for day in days:
        if day["date"] == target_date:
            return day
    return None

def get_current_and_next_event(events, current_time):
    """
    Return a tuple (current_event, next_event) based on the current time.
    
    - current_event is the event in progress (if any).
    - next_event is the upcoming event with start time after current_time.
    """
    current_event = None
    next_event = None
    for event in sorted(events, key=lambda e: e["start"]):
        if event["start"] <= current_time < event["end"]:
            current_event = event
        elif event["start"] > current_time:
            if next_event is None or event["start"] < next_event["start"]:
                next_event = event
    return current_event, next_event

def format_event(event):
    """Return a formatted string for an event: time range and description."""
    start_str = event["start"].strftime("%I:%M %p")
    end_str = event["end"].strftime("%I:%M %p")
    return f"{start_str} - {end_str}: {event['description']}"

def render_main_view(stdscr, current_dt, today_schedule):
    stdscr.clear()
    line = 0
    # Header section with colors
    stdscr.addstr(line, 0, "Plan Scheduler", curses.color_pair(1) | curses.A_BOLD)
    line += 1
    time_str = "Current Date & Time: " + current_dt.strftime("%A, %B %d, %Y %I:%M %p")
    stdscr.addstr(line, 0, time_str, curses.color_pair(2))
    line += 1
    stdscr.addstr(line, 0, "=" * 40, curses.color_pair(1))
    line += 2

    if today_schedule is None:
        stdscr.addstr(line, 0, "No schedule found for today.", curses.color_pair(2))
        line += 2
    else:
        events = sorted(today_schedule["events"], key=lambda e: e["start"])
        current_event, next_event = get_current_and_next_event(events, current_dt)
        
        if current_event:
            remaining = current_event["end"] - current_dt
            remaining_minutes = int(remaining.total_seconds() // 60)
            stdscr.addstr(line, 0, ">> In-progress event:", curses.color_pair(3) | curses.A_BOLD)
            line += 1
            stdscr.addstr(line, 2, format_event(current_event), curses.color_pair(3))
            line += 1
            # Print "Time remaining:" in in-progress event color then the minutes in a different color.
            time_remaining_text = "Time remaining: "
            stdscr.addstr(line, 2, time_remaining_text, curses.color_pair(3))
            stdscr.addstr(line, 2 + len(time_remaining_text), f"{remaining_minutes} minutes", curses.color_pair(5))
            line += 2
        else:
            if events and current_dt < events[0]["start"]:
                stdscr.addstr(line, 0, "Upcoming event:", curses.color_pair(4) | curses.A_BOLD)
                line += 1
                stdscr.addstr(line, 2, format_event(events[0]), curses.color_pair(4))
                line += 2
            else:
                stdscr.addstr(line, 0, "No event currently in progress.", curses.color_pair(2))
                line += 2
        
        if next_event:
            stdscr.addstr(line, 0, "Next upcoming event:", curses.color_pair(2) | curses.A_BOLD)
            line += 1
            stdscr.addstr(line, 2, format_event(next_event), curses.color_pair(2))
            line += 2
        else:
            stdscr.addstr(line, 0, "No further events for today.", curses.color_pair(2))
            line += 2

    stdscr.refresh()

def render_full_schedule_view(stdscr, today_schedule):
    stdscr.clear()
    line = 0
    # Header for full schedule view
    stdscr.addstr(line, 0, "Today's Full Schedule", curses.color_pair(1) | curses.A_BOLD)
    line += 1
    stdscr.addstr(line, 0, "=" * 40, curses.color_pair(1))
    line += 2

    if today_schedule is None:
        stdscr.addstr(line, 0, "No schedule found for today.", curses.color_pair(2))
        line += 2
    else:
        events = sorted(today_schedule["events"], key=lambda e: e["start"])
        for event in events:
            stdscr.addstr(line, 2, format_event(event), curses.color_pair(2))
            line += 1
        line += 1

    stdscr.refresh()

def run_scheduler(stdscr, args, days):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.clear()
    
    # Setup colors if supported
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)    # Titles and divider lines
        curses.init_pair(2, curses.COLOR_WHITE, -1)   # Normal text (default)
        curses.init_pair(3, curses.COLOR_GREEN, -1)   # In-progress event
        curses.init_pair(4, curses.COLOR_YELLOW, -1)  # Upcoming event (for "Upcoming event:" block)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1) # Special color for time remaining digits
    
    simulation_mode = args.simulate is not None
    if simulation_mode:
        try:
            sim_start_dt = datetime.strptime(args.simulate, "%Y-%m-%d %H:%M")
        except ValueError:
            sim_start_dt = datetime.now().replace(second=0, microsecond=0)
        sim_start_wall = datetime.now()

    view_full_schedule = False

    while True:
        if simulation_mode:
            now_wall = datetime.now()
            current_dt = sim_start_dt + (now_wall - sim_start_wall)
        else:
            current_dt = datetime.now()
        current_dt = current_dt.replace(second=0, microsecond=0)

        today_schedule = find_today_schedule(days, current_dt.date())

        if view_full_schedule:
            render_full_schedule_view(stdscr, today_schedule)
        else:
            render_main_view(stdscr, current_dt, today_schedule)

        # Refresh exactly once per minute.
        now_wall = datetime.now()
        next_minute = now_wall.replace(second=0, microsecond=0) + timedelta(minutes=1)
        timeout = (next_minute - now_wall).total_seconds()

        elapsed = 0
        interval = 0.2
        while elapsed < timeout:
            stdscr.timeout(0)
            key = stdscr.getch()
            if key != -1:
                if not view_full_schedule:
                    if key == ord('q'):
                        return  # Exit the program when in main view
                    elif key == ord('t'):
                        view_full_schedule = True
                        break
                else:
                    if key == ord('q'):
                        view_full_schedule = False
                        break
            time.sleep(interval)
            elapsed += interval

def curses_main(args, days):
    curses.wrapper(lambda stdscr: run_scheduler(stdscr, args, days))

def main():
    parser = argparse.ArgumentParser(description="Plan Scheduler in Open Loop (refreshes every minute).")
    parser.add_argument("--simulate", type=str, help="Simulate current datetime e.g. '2025-04-07 09:30'")
    # Get the plan file address from the OS environment variable "plan_file_address"
    plan_file_default = os.environ.get("plan_file_address", "plan.txt")
    parser.add_argument("--plan", type=str, default=plan_file_default, help="Path to the plan file (default from env var 'plan_file_address')")
    args = parser.parse_args()

    try:
        days = parse_plan_file(args.plan)
    except FileNotFoundError:
        print(f"Error: Plan file '{args.plan}' not found.")
        sys.exit(1)
    
    curses_main(args, days)

if __name__ == "__main__":
    main()