import logging
import time
from datetime import datetime
from functools import wraps

import speedsnake.core.logging as speedtest_logging
import speedsnake.data.parquet as parquet
import speedsnake.data.results as results
import speedsnake.service.environment as env
import speedsnake.service.s3 as s3
import speedsnake.service.speedtest as speedtest

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


def check_and_upload_parquets() -> None:
    """Upload all parquet files in uploads/ to S3 with checksum verification."""
    upload_dir = env.get_upload_dir()
    parquet_files = list(upload_dir.rglob("*.parquet"))

    if not parquet_files:
        logger.debug("No parquet files to upload")
        return

    logger.info(f"Found {len(parquet_files)} parquet files to upload")

    session = s3.assume_role()
    config = s3.read_app_config(session)
    bucket = config["s3_bucket_name"]

    for parquet_path in parquet_files:
        try:
            local_md5 = s3.calculate_md5(parquet_path)
            s3_key = s3.construct_s3_key(parquet_path, upload_dir)
            etag = s3.upload_parquet_file(parquet_path, s3_key, bucket, session)

            if not s3.verify_upload_checksum(local_md5, etag):
                logger.error(f"Checksum mismatch for {parquet_path}, preserving local file")
                continue

            parquet_path.unlink()
            logger.info(f"Uploaded and deleted {parquet_path} → s3://{bucket}/{s3_key}")

        except Exception as e:
            logger.error(f"Failed to upload {parquet_path}: {e}")


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

                try:
                    check_and_upload_parquets()
                except Exception as e:
                    logger.error(f"S3 upload error: {e}")

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
