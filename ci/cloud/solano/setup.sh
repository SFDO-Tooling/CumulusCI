#!/bin/bash

# Install python libraries
pip install --upgrade simple-salesforce
pip install --upgrade selenium
pip install --upgrade requests
pip install --upgrade PyGithub==1.25.1

# remember where we came from
BASEDIR=`pwd`

# clone the CumulusCI repository
cd /tmp
git clone https://github.com/SalesforceFoundation/CumulusCI
cd CumulusCI
git fetch --all
git checkout features/cloud-ci-integrations
git pull

# return to repo
cd $BASEDIR
