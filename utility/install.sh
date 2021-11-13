set -e
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
xattr -dr com.apple.quarantine $SCRIPT_DIR  # turn off Apple's quarantine warnings
                                            # TODO: review this with Security!
$SCRIPT_DIR/python/bin/python3 $SCRIPT_DIR/python/bin/venv_from_pip.py
CCIBIN=~/.cumulusci/cci_python_env/bin/
RUNDIR=~/.cumulusci/cci_python_env/run/
ln $CCIBIN/python3 $CCIBIN/python
$CCIBIN/python $CCIBIN/ensure_dir_in_path.py $RUNDIR
ls $RUNDIR/cci
echo "Cumulusci installed in $RUNDIR"