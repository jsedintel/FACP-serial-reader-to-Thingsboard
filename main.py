import os
from config.loader import load_and_validate_config, load_event_severity_levels
from logging_setup import setup_logging
from app.core import Application

def main():
    # Setup logging
    config_path = os.path.join("config", "logging_config.yml")
    setup_logging(config_path)

    # Load configurations
    config = load_and_validate_config(os.path.join("config", "config.yml"))
    event_severity_levels = load_event_severity_levels(os.path.join("config", "eventSeverityLevels.yml"))

    # Initialize and run the application
    app = Application(config, event_severity_levels)
    app.start()

if __name__ == "__main__":
    main()