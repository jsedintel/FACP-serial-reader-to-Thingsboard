import os
import subprocess
from datetime import datetime, time
from time import sleep
import requests


def get_latest_release():
    """
    Fetches the latest release information from the GitHub repository.
    Uses the requests library to get the JSON data and extracts the tag name of the latest release.

    Returns:
        str: The tag name of the latest release.
    """
    url = 'https://api.github.com/repos/Andres10976/Serial_to_Mqtt_Gateway_for_FACP/releases/latest'
    response = requests.get(url)
    latest_release = response.json()
    latest_tag = latest_release['tag_name']
    return latest_tag


def check_zip_file(latest_tag):
    """Checks if the zip file corresponding to the latest release exists.

    If the zip file doesn't exist, triggers the update script (updateApp.sh).

    Args:
        latest_tag (str): The tag name of the latest release.
    """

    zip_file = f"{latest_tag}.zip"
    if not os.path.exists(zip_file):
        print("yeah nigga")
        #subprocess.run(['./updateApp.sh'])


def is_update_time():
    """Checks if the current time is within the designated update window.

    The update window is currently set between 00:00 and 01:00 (inclusive).

    Returns:
        bool: True if the current time is within the update window, False otherwise.
    """

    current_time = datetime.now().time()
    return current_time >= time(0, 0) and current_time <= time(1, 0)


def update_check_thread():
    """Continuously checks for updates at a specified interval.

    The interval is currently set to 60 seconds (1 minute). If an update is available
    during the designated update window, the update script is triggered.
    """

    while True:
        #if is_update_time():
        latest_tag = get_latest_release()
        check_zip_file(latest_tag)
        sleep(60)  # Update check interval (in seconds)
