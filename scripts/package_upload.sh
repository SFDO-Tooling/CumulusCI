#!/bin/bash

echo "--- Starting Xvfb"
Xvfb -fp /usr/share/fonts/X11/misc/ :22 -screen 0 1024x768x16 2>&1 &

export DISPLAY=":22"

echo "--- Starting Selenium Server"
java -jar /var/lib/jenkins/workspace/selenium-server-standalone-2.42.0.jar -port 4444 -multiWindow -browserSessionReuse -timeout 30000 -forcedBrowserModeRestOfLine "*firefox /usr/lib/firefox/firefox" -log "selenium.log" 2>&1 &

echo "--- Waiting 3 seconds for Selenium Server to start"
sleep 3

echo "--- Running Package Upload"
source ../venv/bin/activate
python ../CumulusCI/scripts/package_upload.py
exit_status=$?

echo "--- Stopping Selenium Server"
kill -9 `ps -eo pid,args | grep "selenium.*-port 4444" | grep -v grep| awk '{ print $1 }'`

echo "--- Stopping Xvfb"
kill -9 `ps -eo pid,args  | grep "Xvfb.*:22" | grep -v grep| awk '{ print $1 }'`

exit $exit_status
