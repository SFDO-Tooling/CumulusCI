#!/bin/bash

# Wrapper script around ant that provides better output for CumulusCI build targets
# NOTE: Requires the stdbuf command to be available.  If on OS X, use brew install coreutils

NORMAL=`echo -e '\033[0m'`
BLACK=`echo -e '\033[30m'`
BLUE=`echo -e '\033[34m'`
PURPLE=`echo -e '\033[35m'`
GREEN=`echo -e '\033[32m'`
RED=`echo -e '\033[31m'`
GREY=`echo -e '\033[37m'`

STDBUF=`which stdbuf`
if [ $? == 1 ]; then
    if [ `uname` == 'Darwin' ]; then
        export PATH=/usr/local/opt/coreutils/libexec/gnubin:$PATH
        STDBUF=`which stdbuf`
        if [ $? == 1 ]; then
            echo "stdbuf not found.  OS X users can use Homebrew with the command 'brew install coreutils' to install stdbuf"
            exit 2
        fi
    else
        echo "The stdbuf is required but was not found"
        exit 2
    fi
fi

target=$@
ant $target 2>&1 | stdbuf -oL \
    stdbuf -o L grep -v '^  *\[copy\]' | \
    stdbuf -o L grep -v '^  *\[delete\]' | \
    stdbuf -o L grep -v '^  *\[loadfile\]' | \
    stdbuf -o L grep -v '^  *\[mkdir\]' | \
    stdbuf -o L grep -v '^  *\[move\]' | \
    stdbuf -o L grep -v '^  *\[xslt\]' | \
    # Highlight entering ant target
    stdbuf -o L sed -e "s/^[a-z|A-Z|_|-|0-9][a-z|A-Z|_|-|0-9-]*:$/$BLUE&$NORMAL/g" | \
    # Highlight deployment status
    stdbuf -o L sed -e "s/^.*\*\** DEPLOYMENT SUCCEEDED \*\**$/$GREEN&$NORMAL/g" | \
    stdbuf -o L sed -e "s/^.*\*\** DEPLOYMENT FAILED \*\**$/$RED&$NORMAL/g" | \
    # Dim the Pending and InProgress messsages during deployment
    stdbuf -o L sed -e "s/^\[sf:.*\] Request Status: InProgress.*$/$GREY&$NORMAL/g" | \
    stdbuf -o L sed -e "s/^\[sf:.*\] Request Status: Pending.*$/$GREY&$NORMAL/g" | \
    # Highlight retrieve/deploy status
    stdbuf -o L sed -e "s/^\[sf:.*\] Request for a .* submitted successfully\.$/$GREEN&$NORMAL/g" | \
    stdbuf -o L sed -e "s/^\[sf:.*\] Request ID for the current .* task: .*$/$GREY&$NORMAL/g" | \
    stdbuf -o L sed -e "s/^\[sf:.*\] Waiting for server to finish processing the request.*$/$GREY&$NORMAL/g" | \
    stdbuf -o L sed -e "s/^\[sf:.*\] Request Status: Succeeded.*$/$GREEN&$NORMAL/g" | \
    stdbuf -o L sed -e "s/^\[sf:.*\] Request Status: Succeeded.*$/$GREEN&$NORMAL/g" | \
    stdbuf -o L sed -e "s/^\[sf:.*\] Finished request .* successfully\.$/$GREEN&$NORMAL/g" | \
    stdbuf -o L sed -e "s/^\[sf:.*\] Request Status: Failed.*$/$RED&$NORMAL/g" | \
    # Highlight retrieve/deploy warnings and errors
    stdbuf -o L sed -e "s/^.*[0-9][0-9]*\..*-- Warning:.*$/$PURPLE&$NORMAL/g" | \
    stdbuf -o L sed -e "s/^.*[0-9][0-9]*\..*-- Error:.*$/$RED&$NORMAL/g" | \
    # Highlight final build status
    stdbuf -o L sed -e "s/^.*BUILD SUCCESSFUL.*$/$GREEN&$NORMAL/g" | \
    stdbuf -o L sed -e "s/^.*BUILD FAILED.*$/$RED&$NORMAL/g"

exit_status=${PIPESTATUS[0]}
    
exit $exit_status
