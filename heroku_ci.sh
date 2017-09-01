#!/bin/bash
# This script runs the tests on Heroku CI

git clone -b "$HEROKU_TEST_RUN_BRANCH" --single-branch https://github.com/SalesforceFoundation/CumulusCI 
cd CumulusCI
git checkout $HEROKU_TEST_RUN_COMMIT_VERSION
nosetests --with-tap --tap-stream --with-coverage --cover-package=cumulusci
coveralls
