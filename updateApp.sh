#!/bin/bash

# Change directory to /home/admin/Desktop/app
cd /home/admin/Desktop/app

# Get the latest release information from the GitHub repository
latest_release=$(curl -s https://api.github.com/repos/Andres10976/Serial_to_Mqtt_Gateway_for_FACP/releases/latest)

# Extract the tag name of the latest release
latest_tag=$(echo "$latest_release" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

# Check if the latest release is already downloaded
if [ ! -f "$latest_tag.zip" ]; then
    # Download the source code ZIP file of the latest release
    wget "https://github.com/Andres10976/Serial_to_Mqtt_Gateway_for_FACP/archive/$latest_tag.zip" -O "$latest_tag.zip"

    # Unzip the source code
    unzip "$latest_tag.zip"

    # Move the files from the unzipped folder to the current directory
    mv "Serial_to_Mqtt_Gateway_for_FACP-$latest_tag"/* .

    # Remove the unzipped folder
    rm -rf "Serial_to_Mqtt_Gateway_for_FACP-$latest_tag"

    # Activate the virtual environment
    source .venv/bin/activate

    # Build the executable using PyInstaller
    pyinstaller --onefile --add-data "config/logging_config.yml":"config" main.py

    # Rename the executable to "app"
    mv dist/main dist/app

    # Move the "app" executable to the current directory
    mv dist/app .

    # Deactivate the virtual environment
    deactivate
fi

# Restart the serial_to_mqtt service
sudo systemctl restart serial_to_mqtt.service