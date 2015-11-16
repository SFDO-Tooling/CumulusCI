#!/bin/bash

# Wrapper script around ant that provides better output for CumulusCI build targets
# NOTE: Requires the stdbuf command to be available.  If on OS X, use brew install coreutils

NORMAL=`echo -e '\033[0m'`
BLACK=`echo -e '\033[30m'`
BLUE=`echo -e '\033[34m'`
GREEN=`echo -e '\033[32m'`
RED=`echo -e '\033[31m'`

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

target=$1
ant $target  | stdbuf -oL \
    stdbuf -o L grep -v '^  *\[copy\]' | \
    stdbuf -o L grep -v '^  *\[delete\]' | \
    stdbuf -o L grep -v '^  *\[loadfile\]' | \
    stdbuf -o L grep -v '^  *\[mkdir\]' | \
    stdbuf -o L grep -v '^  *\[move\]' | \
    stdbuf -o L grep -v '^  *\[xslt\]' | \
    stdbuf -o L sed -e "s/^[a-z|A-Z|_|-|0-9][a-z|A-Z|_|-|0-9-]*:$/$BLUE&$NORMAL/g" | \
    stdbuf -o L sed -e "s/^BUILD SUCCESSFUL$/$GREEN&$NORMAL/g" | \
    stdbuf -o L sed -e "s/^BUILD FAILED$/$RED&$NORMAL/g"

exit_status=${PIPESTATUS[0]}
    
exit $exit_status
