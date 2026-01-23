import logging
import time
from datetime import datetime
from functools import wraps

import speedtest.core.logging as speedtest_logging
import speedtest.data.parquet as parquet
import speedtest.data.results as results
import speedtest.service.environment as env
import speedtest.service.speedtest as speedtest

logger = logging.getLogger(__name__)


def sleep(seconds: int):
    logger.info(f"sleeping for {seconds} seconds")
    time.sleep(seconds)


def check_and_convert_complete_days() -> None:
    """Check for complete days and convert to parquet."""
    today = datetime.now().strftime("%Y-%m-%d")
    complete_days = parquet.get_complete_days(env.get_result_dir(), today)

    if not complete_days:
        logger.debug("No complete days to convert")
        return

    logger.info(f"Found {len(complete_days)} complete days to convert: {complete_days}")

    location_uuid = env.get_speedtest_location_uuid()

    for day_str in complete_days:
        try:
            # Parse day string to reconstruct partition paths
            year, month, day = day_str.split("-")

            # Construct CSV partition path
            csv_partition = env.get_result_dir() / f"year={year}" / f"month={month}" / f"day={day}"

            # Construct parquet partition path with location
            parquet_partition = (
                env.get_upload_dir() / f"location={location_uuid}" / f"year={year}" / f"month={month}" / f"day={day}"
            )

            # Convert day to parquet
            parquet_path = parquet.convert_day_to_parquet(csv_partition, parquet_partition)

            logger.info(f"Successfully converted {day_str} to {parquet_path}")

        except Exception as e:
            logger.error(f"Failed to convert {day_str}: {e}")


def loop(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        while True:
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error occurred: {e}")
            finally:
                try:
                    check_and_convert_complete_days()
                except Exception as e:
                    logger.error(f"Parquet conversion error: {e}")
                sleep(env.get_sleep_seconds())

    return wrapper


@loop
def run():
    res = speedtest.run()

    partition_dir = results.get_hive_partition_path(env.get_result_dir(), res["timestamp"])
    filename = results.get_csv_filename(res["timestamp"])
    filepath = partition_dir / filename

    results.write_csv(filepath, res)


def main():
    speedtest_logging.setup_logging()
    logger.info("Starting speedtest loop")
    try:
        run()
    except KeyboardInterrupt:
        logger.warning("interrupt signal received, exiting gracefully")


if __name__ == "__main__":
    main()
