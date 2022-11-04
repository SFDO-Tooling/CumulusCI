#!/bin/bash

CHROME_VERSION=$(dpkg-query --showformat='${Version}' --show google-chrome-stable | cut -d\. -f1-3)
CHROMEDRIVER_VERSION=$1
if [ -z "$2" ]; then
    CHROMEDRIVER_VERSION=$(wget -q -O - "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION")
else
    CHROMEDRIVER_VERSION=$2
fi


wget -q --continue -P $CHROMEDRIVER_DIR "http://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
unzip $CHROMEDRIVER_DIR/chromedriver* -d $CHROMEDRIVER_DIR
