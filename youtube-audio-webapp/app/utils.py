def setup_logging():
    import logging
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def create_output_directory(output_dir):
    from pathlib import Path

    Path(output_dir).mkdir(parents=True, exist_ok=True)


def handle_error(logger, error_message):
    logger.error(error_message)
    return {"error": error_message}