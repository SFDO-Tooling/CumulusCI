#!/bin/sh

OUT_FILE="$1" || exit 1

ENV_DIR="$(mktemp -d)" || exit 1
RES_FILE="$(mktemp)" || exit 1
PYPI_JSON="$(mktemp)" || exit 1

echo " "
echo "=> Collecting package info from PyPI..."
echo " "
curl -L "https://pypi.io/pypi/cumulusci/json" > "$PYPI_JSON" || exit 1
PACKAGE_URL="$(cat "$PYPI_JSON" | jq '.urls[1].url')" || exit 1
PACKAGE_SHA="$(cat "$PYPI_JSON" | jq '.urls[1].digests.sha256')" || exit 1
PACKAGE_VERSION="$(cat cumulusci/version.txt)"

echo " "
echo "=> Creating a temporary virtualenv and installing CumulusCI..."
echo " "
python3.7 -m venv "$ENV_DIR" || exit 1
source "$ENV_DIR/bin/activate" || exit 1
pip install -U pip
pip install --no-cache-dir cumulusci==$PACKAGE_VERSION homebrew-pypi-poet || exit 1

echo " "
echo "=> Collecting dependencies and generating resource stanzas..."
echo " "
poet cumulusci | awk '/resource "cumulusci"/{c=5} !(c&&c--)' > "$RES_FILE"
if [ $? -ne 0 ]; then
   exit 1
fi

echo " "
echo "=> Writing Homebrew Formula to ${OUT_FILE}..."
echo " "
cat << EOF > $OUT_FILE
class Cumulusci < Formula
  include Language::Python::Virtualenv

  desc "Python framework for building automation for Salesforce projects"
  homepage "https://github.com/SFDO-Tooling/CumulusCI"
  url $PACKAGE_URL
  sha256 $PACKAGE_SHA
  head "https://github.com/SFDO-Tooling/CumulusCI.git"

  depends_on "python"

$(cat "$RES_FILE")

  def install
    xy = Language::Python.major_minor_version "python3"
    site_packages = libexec/"lib/python#{xy}/site-packages"
    ENV.prepend_create_path "PYTHONPATH", site_packages

    system "python3", *Language::Python.setup_install_args(libexec)

    deps = resources.map(&:name).to_set
    deps.each do |r|
      resource(r).stage do
        system "python3", *Language::Python.setup_install_args(libexec)
      end
    end

    bin.install Dir["#{libexec}/bin/cci"]
    bin.install Dir["#{libexec}/bin/snowfakery"]
    bin.env_script_all_files(libexec/"bin", :PYTHONPATH => ENV["PYTHONPATH"])
  end

  test do
    system bin/"cci", "version"
  end
end
EOF

echo "Done!"
