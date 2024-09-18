#!/bin/bash

# Set the path to your virtual environment
VENV_PATH="/home/edintel/Desktop/app/.venv"

# Set the path to your Python script
PYTHON_SCRIPT="/home/edintel/Desktop/app/main.py"

# Set the path of the project
PROJECT_PATH="/home/edintel/Desktop/app"

# Install requirements
sudo "$VENV_PATH/bin/pip" install -r "$PROJECT_PATH/requirements.txt"

# Run your Python script
sudo "$VENV_PATH/bin/python3" "$PYTHON_SCRIPT"