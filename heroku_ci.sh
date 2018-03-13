#!/bin/bash
# This script runs the tests on Heroku CI

# Clone the Github repo to the right branch/commit to generate a .git folder for use in /app
git clone -b "$HEROKU_TEST_RUN_BRANCH" --single-branch https://github.com/SalesforceFoundation/CumulusCI 
cd CumulusCI
git reset --hard $HEROKU_TEST_RUN_COMMIT_VERSION
cd /app
mv CumulusCI/.git .

failed=0

# Run the CumulusCI Unit Tests
nosetests --with-tap --tap-stream --with-coverage --cover-package=cumulusci
exit_status=$?
if [ "$exit_status" != "0" ]; then
    failed=1
fi


# If the last commit message contains [skip CumulusCI-Test], skip running any test flows
git log -n 1 | grep '\[skip CumulusCI-Test\]' > /dev/null
exit_status=$?
if [ "$exit_status" == "0" ]; then
    echo "Found [skip CumulusCI-Test] in the commit message, skipping cci flow test runs"
    coveralls
    exit $failed
fi

# For feature branches, skip running the CumulusCI-Test flows if there is not an open PR unless the last commit message contains [run CumulusCI-Test]
if [ "$HEROKU_TEST_RUN_BRANCH" != "master" ] &&\
   [[ "$HEROKU_TEST_RUN_BRANCH" == feature/* ]]; then
    echo "Checking for open pull request to determine next testing steps"
    pr=`python scripts/has_open_pr.py "$HEROKU_TEST_RUN_BRANCH"`
    git log -n 1 | grep '\[run CumulusCI-Test\]' > /dev/null
    exit_status=$?
    if [ "$pr" == "" ] && [ "$exit_status" != "0" ]; then
        # If there is not an open PR, don't run the CumulusCI-Test flows
        coveralls
        exit $failed
    fi
fi

# Run the robot tests for the CumulusCI and Salesforce library
echo "--------------------------------------------"
echo "Running CumulusCI and Salesforce robot tests"
echo "--------------------------------------------"

cci org info dev

# Start TAP output
echo "1...2"

coverage run --append --source=cumulusci `which cci` task run robot --org dev -o suites cumulusci/robotframework/tests/cumulusci | tee robot_cumulusci.log
exit_status=${PIPESTATUS[0]}
if [ "$exit_status" == "0" ]; then
    echo "ok 1 - CumulusCI robot tests passed"
else
    echo "not ok 1 - Failed CumulusCI robot tests: `cat robot_cumulusci.log`"
    failed=1
fi

coverage run --append --source=cumulusci `which cci` task run robot --org dev -o vars BROWSER:headlesschrome,CHROME_BINARY:$GOOGLE_CHROME_BIN -o suites cumulusci/robotframework/tests/salesforce | tee robot_salesforce.log
exit_status=${PIPESTATUS[0]}
if [ "$exit_status" == "0" ]; then
    echo "ok 2 - Salesforce robot tests passed"
else
    echo "not ok 2 - Failed Salesforce robot tests: `cat robot_salesforce.log`"
    failed=1
fi

cci org scratch_delete dev

# Clone the CumulusCI-Test repo to run test builds against it with cci
echo "------------------------------------------"
echo "Running test builds against CumulusCI-Test"
echo "------------------------------------------"
echo ""
echo "Cloning https://github.com/SalesforceFoundation/CumulusCI-Test"
git clone https://github.com/SalesforceFoundation/CumulusCI-Test
cd CumulusCI-Test
if [ "$HEROKU_TEST_RUN_BRANCH" == "master" ] ||\
   [[ "$HEROKU_TEST_RUN_BRANCH" == feature/* ]] ; then
    # Start TAP output
    echo "1...4"

    # Run ci_feature
    coverage run --append --source=../cumulusci `which cci` flow run ci_feature --org scratch --delete-org | tee cci.log
    exit_status=${PIPESTATUS[0]}
    if [ "$exit_status" == "0" ]; then
        echo "ok 1 - Successfully ran ci_feature"
    else
        echo "not ok 1 - Failed ci_feature: `tail -1 cci.log`"
        failed=1
    fi
        
    # Run ci_beta
    coverage run --append --source=../cumulusci `which cci` flow run ci_beta --org scratch --delete-org | tee -a cci.log
    exit_status=${PIPESTATUS[0]}
    if [ "$exit_status" == "0" ]; then
        echo "ok 4 - Successfully ran ci_beta"
    else
        echo "not ok 4 - Failed ci_beta: `tail -1 cci.log`"
        failed=1
    fi

    # Run ci_master
    coverage run --append --source=../cumulusci `which cci` flow run ci_master --org packaging | tee -a cci.log
    exit_status=${PIPESTATUS[0]}
    if [ "$exit_status" == "0" ]; then
        echo "ok 2 - Successfully ran ci_master"
    else
        echo "not ok 2 - Failed ci_master: `tail -1 cci.log`"
        failed=1
    fi

    # Run release_beta
    coverage run --append --source=../cumulusci `which cci` flow run release_beta --org packaging | tee -a cci.log
    exit_status=${PIPESTATUS[0]}
    if [ "$exit_status" == "0" ]; then
        echo "ok 3 - Successfully ran release_beta"
    else
        echo "not ok 3 - Failed release_beta: `tail -1 cci.log`"
        failed=1
    fi

fi

# Combine the CumulusCI-Test test coverage with the nosetest coverage
echo "Combining .coverage files"
cd ..
coverage combine .coverage CumulusCI-Test/.coverage

# Record to coveralls.io
coveralls

exit $failed
