# cumulusci: The command line interface to CumulusCI

# Setting up your local environment
The cumulusci command is written in Python and is designed to run in a Python virtualenv.  If you don't know what that is, no problem.  Follow the steps below to set up a virtualenv so you can run the cumulusci command yourself.

## Check out CumulusCI

First, you'll need to clone a copy of CumulusCI.  Go to wherever you keep development workspaces on your computer.

    git clone git@github.com:SalesforceFoundation/CumulusCI
    cd CumulusCI
    export CUMULUSCI_PATH=`pwd`

## Installing virtualenv on OS X

The easiest way to get virtualenv on OS X is using Homebrew.  The instructions below assume you already have the brew command

    brew install python

Then, continue along...

## Installing virtualenv

If you don't have the virtualenv command available, you can install it with pip:

    pip install virtualenv

## Creating your virtualenv (venv)

The virtualenv command allows you to build isolate python virtual environments in subfolders which you can easily activate and deactivate from the command line.  This keeps your modules isolated from your system's python and is generally a good idea.  It's also really easy.

    virtualenv venv
    source venv/bin/activate
    which python
        PATH_TO_YOUR_VENV/bin/python
    which pip
        PATH_TO_YOUR_VENV/bin/pip
    
At this point, your virtualenv is activated.  Your shell PATH points to python and pip (Python's package installer) inside your virtualenv.  Anything you install is isolated there.

## Installing the cumulusci command and dependencies

To initialize the cumulusci command, you need to run the following once inside your virtualenv:

    pip install -r requirements.txt

When the installation completes, you should be able to run the cumulusci command

    cumulusci
        Usage: cumulusci [OPTIONS] COMMAND [ARGS]...
        
        Options:
          --help  Show this message and exit.
        
        Commands:
          ci       Commands to make building on CI servers...
          dev      Commands useful to developers in interacting...
          github   Commands for interacting with the Github...
          release  Commands used in the release process and...

As long as your virtualenv is activated, you can go into any repository configured for CumulusCI and use the cumulusci command to perform actions against it.

## Exiting and re-entering your virtualenv

If you start a new terminal session, you will need to initialize your virtualenv.

    cd PATH/TO/CumulusCI
    source venv/bin/activate

To leave your virtualenv

    deactivate

If you want to always have the cumulusci command available, you can add the following lines to your .bash_profile (or similar)

    export CUMULUSCI_PATH=PATH/TO/CumulusCI
    source $CUMULUSCI_PATH/venv/bin/activate

# Environment Variables

Most commands in cumulusci require credentials to external systems.  All credentials in the cumulusci command are passed via environment variables to avoid them ever being stored insecurely in files.

## Salesforce Org Credentials

* SF_USERNAME
* SF_PASSWORD: Append security token to password if needed
* SF_SERVERURL: (optional) Override the default login url: https://login.salesforce.com

## Packaging Org OAuth Credentials

For more information on how to get these values, see https://cumulusci-oauth-tool.herokuapp.com

* OAUTH_CLIENT_ID
* OAUTH_CLIENT_SECRET
* OAUTH_CALLBACK_URL
* REFRESH_TOKEN
* INSTANCE_URL

## Github

* GITHUB_ORG_NAME
* GITHUB_REPO_NAME
* GITHUB_USERNAME
* GITHUB_PASSWORD: Usage of an application token is recommended instead of passwords

## Custom Branch and Tag Naming

CumulusCI defaults to the branch and tag prefixes shown below.  If you're using these, you don't need to configure anything:

* Master Branch: master
* Beta Release Tag: beta/
* Production Release Tag: release/

You can override any of these values with the following environment variables:

* MASTER_BRANCH
* PREFIX_BETA
* PREFIX_RELEASE


# Full help text for the cumulusci command

## cumulusci

cumulusci

    Usage: cumulusci [OPTIONS] COMMAND [ARGS]...
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      ci           Commands to make building on CI servers...
      dev          Commands useful to developers in interacting...
      github       Commands for interacting with the Github...
      mrbelvedere  Commands for interacting with mrbelvedere
      release      Commands used in the release process and...

## (dev) For Developers

cumulusci dev

    Detected build information: {}
    Usage: cumulusci dev [OPTIONS] COMMAND [ARGS]...
    
      Commands useful to developers in interacting with Salesforce package
      source metadata
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      apextestsdb_upload  Upload a test_results.json file to the...
      deploy              Runs a full deployment of the code including...
      deploy_managed      Installs a managed package version and...
      run_tests           Run Apex tests in the target org via the...
      update_package_xml  Updates the src/package.xml file by parsing...

cumulusci dev apextestsdb_upload --help

    Detected build information: {}
    Usage: cumulusci dev apextestsdb_upload [OPTIONS] EXECUTION_NAME
                                            RESULTS_FILE_URL
    
      Upload a test_results.json file to the ApexTestsDB web application for
      analysis.  NOTE: This does not currently work with local files.  You will
      have to upload the file to an internet accessible web server and provide
      the path.
    
    Options:
      --repo-url TEXT       Set to override the repository url for the report
      --branch TEXT         Set to override the branch for the report
      --commit TEXT         Set to override the commit sha for the report
      --execution-url TEXT  Set to provide a link back to execution results
      --environment TEXT    Set a custom name for the build environment
      --help                Show this message and exit.

cumulusci dev deploy --help

    Detected build information: {}
    Usage: cumulusci dev deploy [OPTIONS]
    
      Runs a full deployment of the code including unused stale package
      metadata, setting up dependencies, deploying the code, and optionally
      running tests
    
    Options:
      --run-tests          If set, run tests as part of the deployment.  Defaults
                           to not running tests
      --full-delete        If set, delete all package metadata at the start of the
                           build instead of doing an incremental delete.
                           **WARNING**: This deletes all package metadata, use
                           with caution.  This option can be necessary if you have
                           reference issues during an incremental delete
                           deployment.
      --ee-org             If set, use the deployUnmanagedEE target which prepares
                           the code for loading into a production Enterprise
                           Edition org.  Defaults to False.
      --deploy-only        If set, runs only the deployWithoutTest target.  Does
                           not clean the org, update dependencies, or run any
                           tests.  This option invalidates all other options
      --debug-logdir TEXT  A directory to store debug logs from each test class.
                           If specified, a TraceFlag is created which captures
                           debug logs.  When all tests have completed, the debug
                           logs are downloaded to the specified directory.  They
                           are then parsed to capture detail information on the
                           test.  See cumulusci dev deploy --json-output for more
                           details
      --help               Show this message and exit.

cumulusci dev deploy_managed --help

    Detected build information: {}
    Usage: cumulusci dev deploy_managed [OPTIONS] COMMIT PACKAGE_VERSION
    
      Installs a managed package version and optionally runs the tests from the
      installed managed package
    
    Options:
      --run-tests  If True, run tests as part of the deployment.  Defaults to
                   False
      --no-exit    If True, do not exit on exception.  Instead, throw the
                   exception so the caller can handle it.  This is used to allow
                   for retrying a managed package installation if the package is
                   unavailable.  Defaults to False
      --help       Show this message and exit.

cumulusci dev run_tests --help

    Detected build information: {}
    Usage: cumulusci dev run_tests [OPTIONS]
    
      Run Apex tests in the target org via the Tooling API and report results.
      Defaults to running all unmanaged test classes ending in _TEST.
    
    Options:
      --test-match TEXT    A SOQL like format value to match against the test
                           name.  Defaults to %_TEST.  You can use commas to
                           separate multiple values like
                           %_SMOKE_TESTS,%_LOAD_TESTS
      --test-exclude TEXT  Similar to --test-match, but adds exclusions to the
                           test name matching.  Defaults to no value.  You can use
                           commas to separate multiple values
      --namespace TEXT     If set, only search for tests inside the specified
                           namespace.  By default, all unmanaged tests are
                           searched
      --debug-logdir TEXT  A directory to store debug logs from each test class.
                           If specified, a TraceFlag is created which captures
                           debug logs.  When all tests have completed, the debug
                           logs are downloaded to the specified directory.  They
                           are then parsed to capture detail information on the
                           test.  See --json-output for more details
      --json-output TEXT   If set, outputs test results data in json format to the
                           specified file.  This option is most useful with the
                           --debug-logs option.  The resulting json file contains
                           detailed information on the code execution structure of
                           each test method including cumulative limits usage both
                           inside and outside the startTest/stopTest context
      --help               Show this message and exit.

cumulusci dev update_package_xml --help

    Detected build information: {}
    Usage: cumulusci dev update_package_xml [OPTIONS]
    
      Updates the src/package.xml file by parsing out the metadata under src/
    
    Options:
      --help  Show this message and exit.

## (release) For Release Managers

cumulusci release

    Detected build information: {}
    Usage: cumulusci release [OPTIONS] COMMAND [ARGS]...
    
      Commands used in the release process and interacting with a Manage Package
      packing org
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      deploy       Runs a full deployment of the code as managed...
      upload_beta  Use Selenium to upload a package version in...

cumulusci release deploy --help

    Detected build information: {}
    Usage: cumulusci release deploy [OPTIONS]
    
      Runs a full deployment of the code as managed code to the packaging org
      including setting up dependencies, deleting metadata removed from the
      repository, deploying the code, and optionally running tests
    
    Options:
      --help  Show this message and exit.

cumulusci release upload_beta --help

    Detected build information: {}
    Usage: cumulusci release upload_beta [OPTIONS] COMMIT
    
      Use Selenium to upload a package version in the packaging org
    
    Options:
      --build-name TEXT    If provided, overrides the build name used to name the
                           package version
      --selenium-url TEXT  If provided, uses a Selenium Server at the specified
                           url.  Example: http://127.0.0.1:4444/wd/hub
      --create-release     If set, creates a release in Github which also creates
                           a tag
      --package TEXT       By default, the package name will be parsed from the
                           cumulusci.properties file in the repo.  Use the package
                           option to override the package name.
      --help               Show this message and exit.

## (github) Github Scripts

cumulusci github

    Detected build information: {}
    Usage: cumulusci github [OPTIONS] COMMAND [ARGS]...
    
      Commands for interacting with the Github repository for the project
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      clone_tag          Create one tag referencing the same commit as...
      commit_status      Set the Github Commit Status for the current...
      master_to_feature  Attempts to merge a commit on the master...
      release            Create a release in Github
      release_notes      Generates release notes by parsing Warning,...

cumulusci github release --help

    Detected build information: {}
    Usage: cumulusci github release [OPTIONS] VERSION COMMIT
    
      Create a release in Github
    
    Options:
      --help  Show this message and exit.

cumulusci github release_notes --help

    Detected build information: {}
    Usage: cumulusci github release_notes [OPTIONS] TAG
    
      Generates release notes by parsing Warning, Info, and Issues headings from
      pull request bodies of all pull requests merged since the last production
      release tag
    
    Options:
      --last-tag TEXT   Instead of looking for the last tag, you can manually
                        provide it.  This is useful if you skip a release and want
                        to build release notes going back 2 releases
      --update-release  If set, add the release notes to the body
      --help            Show this message and exit.

cumulusci github commit_status --help

    Detected build information: {}
    Usage: cumulusci github commit_status [OPTIONS] STATE
    
      Set the Github Commit Status for the current commit.  Acceptible state
      values are pending, success, error, and failure
    
    Options:
      --context TEXT      The context of this status.  This is usually a string to
                          identify a build system
      --url TEXT          A url to the build.  This is usually a link to a build
                          system that ran the build
      --description TEXT  Override the default status description text
      --commit TEXT       By default, the current local commit is used.  You can
                          pass a commit sha here to set status on a different
                          commit
      --help              Show this message and exit.

cumulusci github clone_tag --help
    Detected build information: {}
    Usage: cumulusci github clone_tag [OPTIONS] SRC_TAG TAG
    
      Create one tag referencing the same commit as another tag
    
    Options:
      --help  Show this message and exit.

cumulusci github master_to_feature --help

    Detected build information: {}
    Usage: cumulusci github master_to_feature [OPTIONS]
    
      Attempts to merge a commit on the master branch to all open feature
      branches.  Creates pull requests assigned to the developer of the feature
      branch if a merge conflict occurs.
    
    Options:
      --commit TEXT  By default, the head commit on master will be merged.  You
                     can override this behavior by specifying a commit sha
      --help         Show this message and exit.

## (ci) Continuous Integration

cumulusci ci

    Detected build information: {}
    Usage: cumulusci ci [OPTIONS] COMMAND [ARGS]...
    
      Commands to make building on CI servers easier
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      apextestsdb_upload  Upload a test_results.json file to the...
      beta_deploy         Deploys a beta managed package version by its...
      deploy              Determines the right kind of build for the...
      next_step           A command to calculate and return the next...

cumulusci ci deploy --help

    Detected build information: {}
    Usage: cumulusci ci deploy [OPTIONS]
    
      Determines the right kind of build for the branch and runs the build
      including tests
    
    Options:
      --debug-logdir TEXT  A directory to store debug logs from each test class.
                           If specified, a TraceFlag is created which captures
                           debug logs.  When all tests have completed, the debug
                           logs are downloaded to the specified directory.  They
                           are then parsed to capture detail information on the
                           test.  See cumulusci dev deploy --json-output for more
                           details
      --help               Show this message and exit.

cumulusci ci beta_deploy --help

    Detected build information: {}
    Usage: cumulusci ci beta_deploy [OPTIONS] TAG COMMIT
    
      Deploys a beta managed package version by its git tag and commit
    
    Options:
      --run-tests        If set, run tests as part of the deployment.  Defaults to
                         not running tests
      --retries INTEGER  The number of times the installation should retry
                         installation if the prior attempt failed due to a package
                         unavailable error.  This error is common after uploading
                         a package if the test org is on a different pod.  There
                         is a slight delay in copying newly uploaded packages.
                         Defaults to 3
      --help             Show this message and exit.

cumulusci ci apextestsdb_upload --help

    Detected build information: {}
    Usage: cumulusci ci apextestsdb_upload [OPTIONS] EXECUTION_NAME
                                           RESULTS_FILE_URL
    
      Upload a test_results.json file to the ApexTestsDB web application for
      analysis.  NOTE: This does not currently work with local files.  You will
      have to upload the file to an internet accessible web server and provide
      the path.
    
    Options:
      --repo-url TEXT       Set to override the repository url for the report
      --branch TEXT         Set to override the branch for the report
      --commit TEXT         Set to override the commit sha for the report
      --execution-url TEXT  Set to provide a link back to execution results
      --environment TEXT    Set a custom name for the build environment
      --help                Show this message and exit.

cumulusci ci next_step --help

    Detected build information: {}
    Usage: cumulusci ci next_step [OPTIONS]
    
      A command to calculate and return the next steps for a ci build to run
    
    Options:
      --help  Show this message and exit.

