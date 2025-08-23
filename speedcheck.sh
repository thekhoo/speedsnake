#!/bin/bash

# Determine the directory where this script resides
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo 'running speedtest check...'
SPEEDTEST_RESULTS=$(speedtest --secure --json --bytes)

SPEEDTEST_DATE=$(echo "$SPEEDTEST_RESULTS" | jq -r '.timestamp | split("T")[0]')

SPEEDTEST_RESULT_BASE_FOLDER="${SPEEDTEST_RESULT_DIR:-$SCRIPT_DIR/results}"
SPEEDTEST_RESULT_PATH="${SPEEDTEST_RESULT_BASE_FOLDER}/${SPEEDTEST_DATE}_speedtest.json"

# make sure all parents are also created
mkdir -p "$SPEEDTEST_RESULT_BASE_FOLDER"
echo "saving results to $SPEEDTEST_RESULT_PATH"

# make sure we actuall have results to save
if [ -z "$SPEEDTEST_RESULTS" ]; then
    echo "no results from speedtest"
    exit 1
fi

# check if the file exists already. If it does - merge, else create new array
if [ -f "$SPEEDTEST_RESULT_PATH" ]; then
    # appends new result to existing array
    # input1 - existing filepath
    # input2 - input object
    jq '. += [input]' \
        "$SPEEDTEST_RESULT_PATH" \
        <(echo "$SPEEDTEST_RESULTS") > "${SPEEDTEST_RESULT_PATH}.tmp" \
        && mv "${SPEEDTEST_RESULT_PATH}.tmp" "$SPEEDTEST_RESULT_PATH"
else
    echo "[$SPEEDTEST_RESULTS]" > "$SPEEDTEST_RESULT_PATH"
fi