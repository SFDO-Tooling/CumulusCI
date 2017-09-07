#!/bin/bash
# This script runs the tests on Heroku CI

# Run the CumulusCI Unit Tests
git clone -b "$HEROKU_TEST_RUN_BRANCH" --single-branch https://github.com/SalesforceFoundation/CumulusCI 
cd CumulusCI
git reset --hard $HEROKU_TEST_RUN_COMMIT_VERSION
nosetests --with-tap --tap-stream --with-coverage --cover-package=cumulusci

python setup.py build
python setup.py install

# Clone the CumulusCI-Test repo to run test builds against it with cci
echo "------------------------------------------"
echo "Running test builds against CumulusCI-Test"
echo "------------------------------------------"
echo ""
echo "Cloning https://github.com/SalesforceFoundation/CumulusCI-Test"
git clone https://github.com/SalesforceFoundation/CumulusCI-Test
cd CumulusCI-Test
if [ $HEROKU_TEST_RUN_BRANCH == "master" ]; then
    echo "1...4"
    coverage run --append --source=../cumulusci `which cci` flow run ci_feature --org scratch --delete-org | tee cci.log
    exit_status=$?
    if [ "$exit_status" == "0" ]; then
        echo "ok 1 - Successfully ran ci_feature"
    else
        echo "not ok 1 - Failed ci_feature: `tail -1 cci.log`"
    fi
        
    coverage run --append --source=../cumulusci `which cci` flow run ci_master --org packaging | tee -a cci.log
    exit_status=$?
    if [ "$exit_status" == "0" ]; then
        echo "ok 2 - Successfully ran ci_master"
    else
        echo "not ok 2 - Failed ci_master: `tail -1 cci.log`"
    fi
    coverage run --append --source=../cumulusci `which cci` flow run release_beta --org packaging | tee -a cci.log
    exit_status=$?
    if [ "$exit_status" == "0" ]; then
        echo "ok 3 - Successfully ran release_beta"
    else
        echo "not ok 3 - Failed release_beta: `tail -1 cci.log`"
    fi
    coverage run --append --source=../cumulusci `which cci` flow run ci_beta --org scratch --delete-org | tee -a cci.log
    exit_status=$?
    if [ "$exit_status" == "0" ]; then
        echo "ok 4 - Successfully ran ci_beta"
    else
        echo "not ok 4 - Failed ci_beta: `tail -1 cci.log`"
    fi

else
    echo "1...1"
    coverage run --append --source=../cumulusci `which cci` flow run ci_feature --org scratch --delete-org
    exit_status=$?
    if [ "$exit_status" == "0" ]; then
        echo "ok 1 - Successfully ran ci_feature"
    else
        echo "not ok 1 - Failed ci_feature: `tail -1 cci.log`"
    fi
fi

# Combine the CumulusCI-Test test coverage with the nosetest coverage
cd ..
coverage combine .coverage CumulusCI-Test/.coverage

# Record to coveralls.io
coveralls
