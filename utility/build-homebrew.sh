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

echo " "
echo "=> Creating a temporary virtualenv and installing CumulusCI..."
echo " "
virtualenv "$ENV_DIR" || exit 1
source "$ENV_DIR/bin/activate" || exit 1
pip install cumulusci homebrew-pypi-poet || exit 1

echo " "
echo "=> Collecting dependencies and generating resource stanzas..."
echo " "
# Filter poet's output through awk to delete the cumulusci resource stanza
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

  desc "Python framework for building portable automation for Salesforce projects"
  head "https://github.com/SFDO-Tooling/CumulusCI.git"
  homepage "https://github.com/SFDO-Tooling/CumulusCI"
  url $PACKAGE_URL
  sha256 $PACKAGE_SHA

  depends_on "python3"

$(cat "$RES_FILE")

  def install
    virtualenv_create(libexec, "python3")
    virtualenv_install_with_resources
  end

  test do
    system bin/"cci", "version"
  end
end
EOF

echo "Done!"
