import logging.config
import yaml

def setup_logging(name: str) -> None:
    with open(name, 'r') as f:
        config = yaml.safe_load(f)
        logging.config.dictConfig(config)
