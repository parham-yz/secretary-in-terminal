#!/usr/bin/env python3
# Import necessary modules for terminal UI, regex processing, command line parsing, and datetime manipulation.
import curses          # For terminal UI and rendering
import re              # For regular expression pattern matching
import sys             # For handling system-specific parameters and functions (e.g. exiting)
import argparse        # For parsing command line options and arguments
import time            # For sleeping/delaying execution
import os              # For interacting with the operating system (e.g., accessing environment variables)
from datetime import datetime, date, time as dtime, timedelta  # For working with dates and times

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
    # Open the file and read all lines into a list
    with open(filename, "r") as f:
        lines = f.readlines()
    
    days = []  # List to store each day's schedule
    current_day = None  # Holds the current day schedule being built
    current_events = []  # List to hold events for the current day
    
    # Regex pattern to match a day header line, e.g. "Monday, April 7th, 2025 - No Gym"
    day_header_pattern = re.compile(r"^([A-Za-z]+),\s+([A-Za-z]+)\s+(\d{1,2}(?:st|nd|rd|th)?),\s+(\d{4}).*")
    # Regex pattern to match a schedule event, e.g. "9:00 AM → 10:15 AM: Task details"
    event_pattern = re.compile(r"^(\d{1,2}:\d{2}\s*(?:AM|PM))\s*→\s*(\d{1,2}:\d{2}\s*(?:AM|PM)):\s*(.+)$")
    
    # Iterate over each line from the file
    for line in lines:
        line = line.strip()  # Remove any leading or trailing whitespace
        if line == "":
            continue  # Skip empty lines
        # Check if the line is a day header
        day_header_match = day_header_pattern.match(line)
        if day_header_match:
            # If a day header is found and a previous day exists, finalize it
            if current_day is not None:
                current_day["events"] = current_events  # Assign the collected events to the current day
                days.append(current_day)  # Add the complete day schedule to the list
                current_events = []  # Reset the events list for the next day
            
            # Extract components of the header using regex groups
            weekday_str = day_header_match.group(1)  # e.g. "Monday" (not used further)
            month_str = day_header_match.group(2)    # e.g. "April"
            day_str_with_suffix = day_header_match.group(3)  # e.g. "7th"
            year_str = day_header_match.group(4)     # e.g. "2025"
            # Remove ordinal suffixes (like 'th', 'st', etc.) from the day string
            day_str = re.sub(r"(st|nd|rd|th)", "", day_str_with_suffix)
            try:
                # Convert the extracted month, day, and year to a date object
                day_date = datetime.strptime(f"{month_str} {day_str} {year_str}", "%B %d %Y").date()
            except ValueError:
                # If date conversion fails, assign None (could be handled differently)
                day_date = None
            header = line  # Save full header text (not used in UI but kept for reference)
            # Initialize a new day schedule dictionary
            current_day = {"date": day_date, "header": header, "events": []}
        else:
            # If the line is not a header, check if it describes an event
            event_match = event_pattern.match(line)
            if event_match and current_day is not None:
                # Extract event details: start time, end time, and description
                start_str = event_match.group(1)
                end_str = event_match.group(2)
                description = event_match.group(3)
                try:
                    # Convert start and end time strings into time objects
                    start_time_obj = datetime.strptime(start_str.strip(), "%I:%M %p").time()
                    end_time_obj = datetime.strptime(end_str.strip(), "%I:%M %p").time()
                except Exception:
                    # Skip event if time conversion fails
                    continue
                # Combine the current day's date with the extracted times to form full datetime objects
                start_dt = datetime.combine(current_day["date"], start_time_obj)
                end_dt = datetime.combine(current_day["date"], end_time_obj)
                # Create an event dictionary and add it to the current day's event list
                event = {"start": start_dt, "end": end_dt, "description": description}
                current_events.append(event)
    
    # After processing all lines, append the last day's schedule if it exists
    if current_day is not None:
        current_day["events"] = current_events
        days.append(current_day)
    return days  # Return the list of all day schedules

def find_today_schedule(days, target_date):
    """Return the schedule for the target_date if available, otherwise return None."""
    for day in days:
        if day["date"] == target_date:
            return day  # Found the matching schedule for the target date
    return None  # No schedule exists for the given target date

def format_event(event):
    """Return a formatted string representation of an event including time range and description."""
    # Format start and end times into a readable format (e.g., "09:00 AM")
    start_str = event["start"].strftime("%I:%M %p")
    end_str = event["end"].strftime("%I:%M %p")
    return f"{start_str} - {end_str}: {event['description']}"

def format_event_main(event):
    """Return a formatted string for the main view: event name and aligned time range.

    The event name is cleaned by removing extra details (anything after '[' or '(').
    """
    # Convert start and end datetimes to time strings
    start_str = event["start"].strftime("%I:%M %p")
    end_str = event["end"].strftime("%I:%M %p")
    # Remove any trailing extra details from the description by splitting on '[' or '('
    short_desc = re.split(r'\s*[\[\(]', event["description"])[0].strip()
    time_range = f"{start_str} - {end_str}"
    # Format the event name to a fixed width (20 characters) so that time range aligns
    return f"{short_desc:<20}{time_range}"

def render_main_view(stdscr, current_dt, today_schedule):
    """
    Render the main user interface view of the schedule.
    This view displays the current date and time, any in-progress event,
    as well as upcoming events.
    """
    stdscr.clear()  # Clear the screen for fresh rendering
    line = 0  # Initialize the line counter for text placement
    
    # Render the header of the application with title
    stdscr.addstr(line, 0, "Plan Scheduler", curses.color_pair(1) | curses.A_BOLD)
    line += 1
    # Display the current date and time in a human-friendly format
    time_str = "Current Date & Time: " + current_dt.strftime("%A, %B %d, %Y %I:%M %p")
    stdscr.addstr(line, 0, time_str, curses.color_pair(2))
    line += 1
    # Draw a divider to separate the header from the content
    stdscr.addstr(line, 0, "=" * 40, curses.color_pair(1))
    line += 2

    if today_schedule is None:
        # If there's no schedule for today, show an appropriate message
        stdscr.addstr(line, 0, "No schedule found for today.", curses.color_pair(2))
        line += 2
    else:
        # Sort the day's events by starting time
        events = sorted(today_schedule["events"], key=lambda e: e["start"])
        current_event = None  # Variable to store event currently in progress
        # Determine if an event is currently active based on current time
        for event in events:
            if event["start"] <= current_dt < event["end"]:
                current_event = event
                break

        # Filter upcoming events that are not breaks (case-insensitive check)
        upcoming_non_break = [
            e for e in events 
            if ("break" not in e["description"].lower()) and (e["start"] > current_dt)
        ]

        if current_event:
            # Calculate remaining time for the current event in minutes
            remaining = current_event["end"] - current_dt
            remaining_minutes = int(remaining.total_seconds() // 60)
            # Display header for an event that is currently in-progress
            stdscr.addstr(line, 0, ">> In-progress event:", curses.color_pair(3) | curses.A_BOLD)
            line += 1
            # Render the current event information with time range and name
            stdscr.addstr(line, 2, format_event_main(current_event), curses.color_pair(3))
            line += 1
            # Display the time remaining for the current event
            time_remaining_text = "Time remaining:     "
            stdscr.addstr(line, 2, time_remaining_text, curses.color_pair(3))
            # Choose color based on remaining time (<15 minutes gets a special color)
            if remaining_minutes < 15:
                time_color = curses.color_pair(6)
            else:
                time_color = curses.color_pair(5)
            stdscr.addstr(line, 2 + len(time_remaining_text), f"{remaining_minutes} minutes", time_color)
            line += 2
            # If an upcoming non-break event is available, display the first one
            if upcoming_non_break:
                stdscr.addstr(line, 0, "Next upcoming event:", curses.color_pair(2) | curses.A_BOLD)
                line += 1
                stdscr.addstr(line, 2, format_event_main(upcoming_non_break[0]), curses.color_pair(2))
                line += 2
            else:
                stdscr.addstr(line, 0, "No further events for today.", curses.color_pair(2))
                line += 2
        else:
            # If there is no current event running, display upcoming events if any
            if upcoming_non_break:
                stdscr.addstr(line, 0, "Upcoming event:", curses.color_pair(4) | curses.A_BOLD)
                line += 1
                stdscr.addstr(line, 2, format_event_main(upcoming_non_break[0]), curses.color_pair(4))
                line += 2
                # If more than one upcoming event, also display the next one
                if len(upcoming_non_break) > 1:
                    stdscr.addstr(line, 0, "Next upcoming event:", curses.color_pair(2) | curses.A_BOLD)
                    line += 1
                    stdscr.addstr(line, 2, format_event_main(upcoming_non_break[1]), curses.color_pair(2))
                    line += 2
            else:
                # If no events are in progress or upcoming, inform the user
                stdscr.addstr(line, 0, "No event currently in progress.", curses.color_pair(2))
                line += 2

    stdscr.refresh()  # Refresh the screen to update changes

def render_full_schedule_view(stdscr, today_schedule):
    """
    Render the full schedule view for today.
    This view lists every event in chronological order.
    """
    stdscr.clear()  # Clear the screen for the full schedule view
    line = 0  # Initialize the line counter
    
    # Display the header for the full schedule view
    stdscr.addstr(line, 0, "Today's Full Schedule", curses.color_pair(1) | curses.A_BOLD)
    line += 1
    stdscr.addstr(line, 0, "=" * 40, curses.color_pair(1))
    line += 2

    if today_schedule is None:
        # Inform the user if no schedule exists for today
        stdscr.addstr(line, 0, "No schedule found for today.", curses.color_pair(2))
        line += 2
    else:
        # Sort and display each event with its formatted representation
        events = sorted(today_schedule["events"], key=lambda e: e["start"])
        for event in events:
            stdscr.addstr(line, 2, format_event(event), curses.color_pair(2))
            line += 1
        line += 1

    stdscr.refresh()  # Refresh the screen to present the full schedule

def run_scheduler(stdscr, args, days):
    """
    Main loop for the scheduler.
    Handles setting up the curses screen, rendering views, and processing user input.
    """
    curses.curs_set(0)  # Hide the blinking cursor
    stdscr.nodelay(True)  # Set getch() as non-blocking so that the scheduler can refresh periodically
    stdscr.clear()  # Clear the screen initially
    
    # Initialize terminal colors if the terminal supports them
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)    # Colors for titles and divider lines
        curses.init_pair(2, curses.COLOR_WHITE, -1)   # Default normal text color
        curses.init_pair(3, curses.COLOR_GREEN, -1)   # Color for in-progress event
        curses.init_pair(4, curses.COLOR_YELLOW, -1)  # Color for upcoming event alerts
        curses.init_pair(5, curses.COLOR_MAGENTA, -1) # Color for time remaining digits (regular)
        curses.init_pair(6, curses.COLOR_BLUE, -1)    # Alternative color for time remaining (<15 minutes)
    
    # Determine if simulation mode is enabled via command line arguments
    simulation_mode = args.simulate is not None
    if simulation_mode:
        try:
            # Parse the simulated starting datetime
            sim_start_dt = datetime.strptime(args.simulate, "%Y-%m-%d %H:%M")
        except ValueError:
            # Fallback to current datetime if the provided simulation string is invalid
            sim_start_dt = datetime.now().replace(second=0, microsecond=0)
        sim_start_wall = datetime.now()  # Record the wall-clock start time for simulation

    view_full_schedule = False  # Flag to toggle between main view and full schedule view

    # Main loop that updates and renders the scheduler view
    while True:
        if simulation_mode:
            # Calculate the simulated current datetime based on elapsed wall-clock time
            now_wall = datetime.now()
            current_dt = sim_start_dt + (now_wall - sim_start_wall)
        else:
            # Use the actual current datetime from the system
            current_dt = datetime.now()
        current_dt = current_dt.replace(second=0, microsecond=0)  # Remove seconds and microseconds for display

        # Retrieve today's schedule using the current date
        today_schedule = find_today_schedule(days, current_dt.date())

        # Render the appropriate view based on the toggle flag
        if view_full_schedule:
            render_full_schedule_view(stdscr, today_schedule)
        else:
            render_main_view(stdscr, current_dt, today_schedule)

        # Set timeout so that the view refreshes exactly once a minute.
        now_wall = datetime.now()
        next_minute = now_wall.replace(second=0, microsecond=0) + timedelta(minutes=1)
        timeout = (next_minute - now_wall).total_seconds()

        elapsed = 0
        interval = 0.2  # Interval in seconds to check for input events
        while elapsed < timeout:
            stdscr.timeout(0)  # Non-blocking check for user key press
            key = stdscr.getch()
            if key != -1:
                if not view_full_schedule:
                    # In main view, allow quitting or switching view
                    if key == ord('q'):
                        return  # Exit the application if 'q' is pressed
                    elif key == ord('t'):
                        view_full_schedule = True  # Switch to full schedule view if 't' is pressed
                        break
                else:
                    # In full schedule view, allow toggling back to main view
                    if key == ord('q'):
                        view_full_schedule = False  # Return to main view when 'q' is pressed
                        break
            time.sleep(interval)
            elapsed += interval

def curses_main(args, days):
    """Initialize the curses wrapper with our scheduler function."""
    curses.wrapper(lambda stdscr: run_scheduler(stdscr, args, days))

def main():
    """Parse command line arguments, load the plan file, and start the scheduler."""
    parser = argparse.ArgumentParser(description="Plan Scheduler in Open Loop (refreshes every minute).")
    parser.add_argument("--simulate", type=str, help="Simulate current datetime e.g. '2025-04-07 09:30'")
    # Fetch the plan file path from OS environment variable "plan_file_address" or use "plan.txt" as default.
    plan_file_default = os.environ.get("plan_file_address", "plan.txt")
    parser.add_argument("--plan", type=str, default=plan_file_default, help="Path to the plan file (default from env var 'plan_file_address')")
    args = parser.parse_args()

    try:
        # Attempt to parse the plan file to extract the schedule data
        days = parse_plan_file(args.plan)
    except FileNotFoundError:
        # If the plan file is missing, print an error message and exit
        print(f"Error: Plan file '{args.plan}' not found.")
        sys.exit(1)
    
    # Start the scheduler within the curses environment
    curses_main(args, days)

if __name__ == "__main__":
    # Run the main function when the script is executed directly
    main()