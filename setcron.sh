SPEEDTEST_FILE="${SPEEDTEST_FILEPATH:-"/home/$USER/internet-speed-check/speedcheck.sh"}"
SPEEDTEST_CRON="${SPEEDTEST_CRON_ENTRY:-"*/1 * * * * /bin/bash $SPEEDTEST_FILE"}"

SPEEDTEST_CRON_JOB="${SPEEDTEST_CRON} >> /tmp/speedtest-check.log 2>&1"

# Get current PATH
if [ -n "$PATH" ]; then
  PATH_LINE="PATH=$PATH"
else
  PATH_LINE=""
fi

crontab -l 2>/dev/null | grep -q "$SPEEDTEST_FILE"
if [ $? -ne 0 ]; then
  (crontab -l 2>/dev/null; [ -n "$PATH_LINE" ] && echo "$PATH_LINE"; echo "$SPEEDTEST_CRON_JOB") | crontab -
  echo "Cron job added."
else
  (crontab -l 2>/dev/null | grep -v "$SPEEDTEST_FILE"; [ -n "$PATH_LINE" ] && echo "$PATH_LINE"; echo "$SPEEDTEST_CRON_JOB") | crontab -
  echo "Cron job updated."
fi