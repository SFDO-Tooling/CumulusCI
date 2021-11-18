set -e
if [ $# -lt 2 ]
  then
    echo "Please provide artifact_id and github token."
    echo "e.g. install_from_net.sh 111111111  gho_fjeiofjfjFEJFOIEJFSjfioesjfoeis"
    exit 1
fi

artifactnum=$1
github_token=$2
# github_token=`cci service info github default --plain | grep token | python -c "import sys; print(sys.stdin.read().split()[1])"`
echo $github_token
curl -L -H "Authorization: token $github_token"  https://api.github.com/repos/SFDO-Tooling/CumulusCI/actions/artifacts/$artifactnum/zip --output /tmp/cci_installer.zip
unzip -o /tmp/cci_installer.zip -d /tmp/cci_installer_tmp
unzip -o /tmp/cci_installer_tmp/cci_installer_mac.zip -d /tmp/cci_installer_tmp
sh /tmp/cci_installer_tmp/cci_installer/install.sh
rm -rf /tmp/cci_installer_tmp /tmp/cci_installer.zip
/Users/pprescod/.cumulusci/cci_python_env/run/cci version