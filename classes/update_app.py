import os
import time
import subprocess
from datetime import datetime

def get_latest_release():
    # Get the latest release information from the GitHub repository
    latest_release = subprocess.check_output(['curl', '-s', 'https://api.github.com/repos/Andres10976/Serial_to_Mqtt_Gateway_for_FACP/releases/latest'])
    latest_release = latest_release.decode('utf-8')

    # Extract the tag name of the latest release
    latest_tag = subprocess.check_output(['echo', latest_release, '|', 'grep', '"tag_name":', '|', 'sed', '-E', 's/.*"([^"]+)".*/\\1/'])
    latest_tag = latest_tag.decode('utf-8').strip()

    return latest_tag

def check_zip_file(latest_tag):
    zip_file = f"{latest_tag}.zip"
    if not os.path.exists(zip_file):
        # Run the updateApp.sh script if the zip file doesn't exist
        subprocess.run(['./updateApp.sh'])

def is_update_time():
    current_time = datetime.now().time()
    return current_time >= time(0, 0) and current_time <= time(1, 0)

def update_check_thread():
    while True:
        if is_update_time():
            latest_tag = get_latest_release()
            check_zip_file(latest_tag)
        time.sleep(60)  # Replace X with the desired number of seconds