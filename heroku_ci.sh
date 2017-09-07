#!/bin/bash
# This script runs the tests on Heroku CI

# Run the CumulusCI Unit Tests
git clone -b "$HEROKU_TEST_RUN_BRANCH" --single-branch https://github.com/SalesforceFoundation/CumulusCI 
cd CumulusCI
git reset --hard $HEROKU_TEST_RUN_COMMIT_VERSION
nosetests --with-tap --tap-stream --with-coverage --cover-package=cumulusci
coveralls

# Clone the CumulusCI-Test repo to run test builds against it with cci
cd ..
git clone https://github.com/SalesforceFoundation/CumulusCI-Test
cci flow run ci_feature --org scratch --delete-org
cci flow run ci_master --org packaging
cci flow run release_beta --org packaging
cci flow run ci_beta --org scratch --delete-org
