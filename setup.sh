#!/bin/bash

read -p "Enter the address of your plan file: " PLAN_FILE_ADDRESS
export plan_file_address="$PLAN_FILE_ADDRESS"
echo "plan_file_address is set to: $PLAN_FILE_ADDRESS"

# Determine which shell startup file to update (prefer .zshrc, then .bashrc, else .profile)
if [ -f "$HOME/.zshrc" ]; then
  RCFILE="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
  RCFILE="$HOME/.bashrc"
else
  RCFILE="$HOME/.profile"
fi
echo "Updating settings in: $RCFILE"

# Append the environment variable export if it doesn't already exist
if ! grep -q "^export plan_file_address=" "$RCFILE"; then
  echo "export plan_file_address=\"$PLAN_FILE_ADDRESS\"" >> "$RCFILE"
  echo "Added 'plan_file_address' to $RCFILE"
fi

# Append the alias for the 'sec' command if it doesn't already exist
if ! grep -q "^alias sec=" "$RCFILE"; then
  echo "alias sec='python3 /Users/parham/Dev/secretary-in-terminal/srouce/main.py'" >> "$RCFILE"
  echo "Added alias 'sec' to $RCFILE"
fi

echo "Setup complete! To start using the 'sec' command, run: source $RCFILE"
