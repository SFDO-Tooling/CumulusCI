set -e
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
$SCRIPT_DIR/bin/python3 $SCRIPT_DIR/bin/venv_from_pip.py
