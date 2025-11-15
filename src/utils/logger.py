import logging
from src.utils.settings import settings

def get_logger(name: str):
    """
    Configures and returns a logger.
    """
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s - %(levelname)s - [%(filename)s] - %(message)s",
        handlers=[
            logging.FileHandler(settings.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(name)
