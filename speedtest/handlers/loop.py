import logging
import time
from functools import wraps

import speedtest.data.results as results
import speedtest.environment as env
import speedtest.logging as speedtest_logging
import speedtest.speedtest as speedtest

logger = logging.getLogger(__name__)


def sleep(seconds: int):
    logger.info(f"sleeping for {seconds} seconds")
    time.sleep(seconds)


def loop(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        while True:
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error occurred: {e}")
            finally:
                sleep(env.get_sleep_seconds())

    return wrapper


@loop
def run():
    res = speedtest.run()
    date_str = speedtest.get_date_str_from_result(res)

    filepath = env.get_result_dir() / f"{date_str}_speedtest.json"
    results.update_array(filepath, res)


def main():
    speedtest_logging.setup_logging()
    logger.info("Starting speedtest loop")
    try:
        run()
    except KeyboardInterrupt:
        logger.warning("interrupt signal received, exiting gracefully")


if __name__ == "__main__":
    main()
