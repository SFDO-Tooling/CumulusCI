#!/bin/sh

# https://wizardzines.com/comics/bash-errors/
set -euo pipefail
OUT_FILE="$1"

ENV_DIR="$(mktemp -d)"
REQS_IN_FILE="$(mktemp)"
REQS_FILE="$(mktemp)"
PYPI_JSON="$(mktemp)" 

echo " "
echo "=> Collecting package info from PyPI..."
echo " "
curl -L "https://pypi.io/pypi/cumulusci/json" > "$PYPI_JSON" 
PACKAGE_URL="$(cat "$PYPI_JSON" | jq '.urls[1].url')" 
PACKAGE_SHA="$(cat "$PYPI_JSON" | jq '.urls[1].digests.sha256')" 
PACKAGE_VERSION="$(cat cumulusci/version.txt)"

echo " "
echo "=> Compiling pip requirements including hashes..."
echo " "
echo "cumulusci==$PACKAGE_VERSION" > "$REQS_IN_FILE"
# For a longish thread on why `allow-unsafe`, see https://github.com/pypa/pip/issues/6459
# Here, we're adding it to collect setuptools-rust for the cryptography library.
pip-compile "$REQS_IN_FILE" -o "$REQS_FILE" --generate-hashes --allow-unsafe

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
  license "BSD-3-Clause"
  head "https://github.com/SFDO-Tooling/CumulusCI.git", branch: "main"

  depends_on "python@3.9"

  def install
    xy = Language::Python.major_minor_version "python3"
    site_packages = libexec/"lib/python#{xy}/site-packages"
    ENV.prepend_create_path "PYTHONPATH", site_packages

    reqs = <<-REQS
$(cat "$REQS_FILE")
REQS

    File.write("requirements.txt", reqs)
    ## Python@3.9 no longer includes python3 https://github.com/Homebrew/homebrew-core/pull/107517
    system "python3.9", "-m", "pip", "install", "-r", "requirements.txt", "--require-hashes", "--no-deps", "--ignore-installed", "--prefix", libexec

    bin.install Dir["#{libexec}/bin/cci"]
    bin.install Dir["#{libexec}/bin/snowfakery"]
    bin.env_script_all_files(libexec/"bin", PYTHONPATH: ENV["PYTHONPATH"])
  end

  test do
    system bin/"cci", "version"
  end
end
EOF

echo "Done!"
