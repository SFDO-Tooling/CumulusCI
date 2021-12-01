set -e
if [ $# -lt 1 ]
  then
    echo "Please provide artifact_id."
    echo "e.g. install_from_net.sh 111111111  "
    exit 1
fi

if [[ -z $PUBLIC_GH_REPO_TOKEN ]]; then
    echo "Please provide PUBLIC_GH_REPO_TOKEN environment variable"
    exit 1;
fi

artifactnum=$1
github_token=$PUBLIC_GH_REPO_TOKEN

cciurl=https://api.github.com/repos/SFDO-Tooling/CumulusCI/actions/artifacts/$artifactnum/zip
zip_path=/tmp/cci_installer.zip
alias download_cci="curl -L -H \"Authorization: token $github_token\" $cciurl  --output $zip_path"

retries=3
while ((retries > 0)); do
    download_cci &&
      unzip -t $zip_path && break || echo "Fail" # fake success

    echo "Retrying faied download" 

    ((retries --))
done

unzip -o $zip_path -d /tmp/cci_installer_tmp
unzip -o /tmp/cci_installer_tmp/cci_installer_mac.zip -d /tmp/cci_installer_tmp
sh /tmp/cci_installer_tmp/cci_installer/install.sh
rm -rf /tmp/cci_installer_tmp $zip_path
/Users/pprescod/.cumulusci/cci_python_env/run/cci version