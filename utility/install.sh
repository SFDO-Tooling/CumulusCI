set -e
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
xattr -dr com.apple.quarantine $SCRIPT_DIR  # turn off Apple's quarantine warnings
                                            # TODO: review this with Security!
$SCRIPT_DIR/python//bin/python3 $SCRIPT_DIR/python/bin/venv_from_pip.py
