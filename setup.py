#!/usr/bin/env python3
import os
import sys

def get_rc_file():
    """
    Determine which shell startup file to update.
    Prefer ~/.zshrc, then ~/.bashrc, else ~/.profile.
    """
    home = os.path.expanduser("~")
    zshrc = os.path.join(home, ".zshrc")
    bashrc = os.path.join(home, ".bashrc")
    profile = os.path.join(home, ".profile")
    if os.path.isfile(zshrc):
        return zshrc
    elif os.path.isfile(bashrc):
        return bashrc
    else:
        return profile

def update_rc_file(rc_file, plan_file_address, alias_command):
    """
    Update the RC file with the export statement for 'plan_file_address' and
    the alias for the 'sec' command if they do not already exist.
    """
    # Read current lines
    try:
        with open(rc_file, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    updated = False

    # Format the export and alias lines
    export_line = f'export plan_file_address="{plan_file_address}"\n'
    alias_line = f"alias sec='{alias_command}'\n"

    # Check for existing export for plan_file_address
    if not any(line.startswith("export plan_file_address=") for line in lines):
        lines.append(export_line)
        print(f"Added environment variable export to {rc_file}")
        updated = True
    else:
        print("Environment variable export already exists in RC file.")

    # Check for existing alias for 'sec'
    if not any(line.startswith("alias sec=") for line in lines):
        lines.append(alias_line)
        print(f"Added alias 'sec' to {rc_file}")
        updated = True
    else:
        print("Alias 'sec' already exists in RC file.")

    if updated:
        try:
            with open(rc_file, "w") as f:
                f.writelines(lines)
        except IOError as e:
            print(f"Error writing to {rc_file}: {e}")
            sys.exit(1)
    else:
        print("No changes made to RC file.")

def main():
    # Prompt for the plan file address
    plan_file_address = input("Enter the address of your plan file: ").strip()
    if not plan_file_address:
        print("Plan file address cannot be empty.")
        sys.exit(1)

    # Set the environment variable for the current process
    os.environ["plan_file_address"] = plan_file_address
    print(f"plan_file_address is set to: {plan_file_address}")

    # Determine RC file to update
    rc_file = get_rc_file()
    print(f"Updating settings in: {rc_file}")

    # Define the alias command for 'sec'
    # Change the path below as needed if your main script is in a different location.
    alias_command = "python3 /Users/parham/Dev/secretary-in-terminal/srouce/main.py"

    # Update the RC file with the export and alias
    update_rc_file(rc_file, plan_file_address, alias_command)

    print("\nSetup complete!")
    print(f"To start using the 'sec' command, run: source {rc_file}")

if __name__ == "__main__":
    main()