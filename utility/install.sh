set -e
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
$SCRIPT_DIR/python//bin/python3 $SCRIPT_DIR/python/bin/venv_from_pip.py
