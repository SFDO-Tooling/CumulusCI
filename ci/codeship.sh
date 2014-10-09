# NOTE: This script expects environment variables to be passed for the Salesforce
# credentials to the orgs: feature, master, packaging, beta, release such as...
# SF_USERNAME_FEATURE
# SF_PASSWORD_MASTER
# SF_SERVERURL_PACKAGING

# Setup variables for branch naming conventions using env overrides if set
if [ "$MASTER_BRANCH" == "" ]; then
    MASTER_BRANCH='master'
fi
if [ "$PREFIX_FEATURE" == "" ]; then
    PREFIX_FEATURE='feature/'
fi
if [ "$PREFIX_BETA" == "" ]; then
    PREFIX_BETA='beta/'
fi
if [ "$PREFIX_PROD" == "" ]; then
    PREFIX_PROD='release/'
fi

# Determine build type and setup Salesforce credentials
if [[ $CI_BRANCH == $MASTER_BRANCH ]]; then
    BUILD_TYPE='master'
elif [[ $CI_BRANCH == $PREFIX_FEATURE* ]]; then
    BUILD_TYPE='feature'
elif [[ $CI_BRANCH == $PREFIX_BETA* ]]; then
    BUILD_TYPE='beta'
elif [[ $CI_BRANCH == $PREFIX_PROD* ]]; then
    BUILD_TYPE='release'    
fi

if [ "$BUILD_TYPE" == "" ]; then
    echo "BUILD SKIPPED: Could not determine BUILD_TYPE for $CI_BRANCH"
    exit 0
fi

# The python scripts expect BUILD_COMMIT
export BUILD_COMMIT=$CI_COMMIT_ID

# Cache the main build directory
export BUILD_WORKSPACE=`pwd`

echo
echo "-----------------------------------------------------------------"
echo "Building $CI_BRANCH as a $BUILD_TYPE build"
echo "-----------------------------------------------------------------"
echo

# Function to filter out unneeded ant output from builds
function runAntTarget {
    target=$1
    stdbuf ant $target  | \
        grep -v '^  *\[copy\]' | \
        grep -v '^  *\[delete\]' | \
        grep -v '^  *\[loadfile\]' | \
        grep -v '^  *\[mkdir\]' | \
        grep -v '^  *\[move\]' | \
        grep -v '^  *\[xslt\]'
    
    if [ "$PIPESTATUS[0]" != "0" ]; then
        echo "BUILD FAILED on target $target"
        exit 1
    fi
}

function runAntTargetBackground {
    ant $1 > "$1.cumulusci.log" 2>& 1 &
}

# Function to wait on all background jobs to complete and return exit status
function waitOnBackgroundJobs {
    FAIL=0
    for job in `jobs -p`
    do
    echo $job
        wait $job || let "FAIL+=1"
    done
    
    echo
    echo "-----------------------------------------------------------------"
    if [ $FAIL -gt 0 ]; then
        echo "BUILD FAILED: Showing logs from parallel jobs below"
    else
        echo "BUILD PASSED: Showing logs from parallel jobs below"
    fi
    echo "-----------------------------------------------------------------"
    echo
    for file in *.cumulusci.log; do
        echo
        echo "-----------------------------------------------------------------"
        echo "BUILD LOG: $file"
        echo "-----------------------------------------------------------------"
        echo
        cat $file
    done
    if [ $FAIL -gt 0 ]; then
        exit 1
    fi
}

#---------------------------------
# Run the build for the build type
#---------------------------------

# Master branch commit, build and test a beta managed package
if [ $BUILD_TYPE == "master" ]; then

    if [ "$SF_USERNAME_MASTER" != "" ]; then
        # Get org credentials from env
        export SF_USERNAME=$SF_USERNAME_MASTER
        export SF_PASSWORD=$SF_PASSWORD_MASTER
        export SF_SERVERURL=$SF_SERVERURL_MASTER
        echo "Got org credentials for master org from env"
        
        # Deploy to packaging org
        echo
        echo "-----------------------------------------------------------------"
        echo "ant deployCI - Deploy to master org"
        echo "-----------------------------------------------------------------"
        echo
        #echo "Copying repository to `pwd`/clone2 to run 2 builds in parallel"
        #cd /home/rof/ 
        #cp -a clone clone2
        #cd clone2
        runAntTarget deployCI
    else
        echo
        echo "-----------------------------------------------------------------"
        echo "No master org credentials, skipping master org build"
        echo "-----------------------------------------------------------------"
        echo
    fi

    # Get org credentials from env
    export SF_USERNAME=$SF_USERNAME_PACKAGING
    export SF_PASSWORD=$SF_PASSWORD_PACKAGING
    export SF_SERVERURL=$SF_SERVERURL_PACKAGING
    echo "Got org credentials for packaging org from env"
    
    # Deploy to packaging org
    echo
    echo "-----------------------------------------------------------------"
    echo "ant deployCIPackageOrg - Deploy to packaging org"
    echo "-----------------------------------------------------------------"
    echo

    #echo "Running deployCIPackageOrg from /home/rof/clone"
    #cd /home/rof/clone
    runAntTarget deployCIPackageOrg

    
    #echo
    #echo "-----------------------------------------------------------------"
    #echo "Waiting on background jobs to complete"
    #echo "-----------------------------------------------------------------"
    #echo
    #waitOnBackgroundJobs
    #if [ $? != 0 ]; then exit 1; fi
    
    # Upload beta package
    echo
    echo "-----------------------------------------------------------------"
    echo "Uploading beta managed package via Selenium"
    echo "-----------------------------------------------------------------"
    echo

    echo "Installing python dependencies"
    export PACKAGE=`grep 'cumulusci.package.name.managed=' cumulusci.properties | sed -e 's/cumulusci.package.name.managed *= *//g'`
    # Default to cumulusci.package.name if cumulusci.package.name.managed is not defined
    if [ "$PACKAGE" == "" ]; then
        export PACKAGE=`grep 'cumulusci.package.name=' cumulusci.properties | sed -e 's/cumulusci.package.name *= *//g'`
    fi
    echo "Using package $PACKAGE"
    export BUILD_NAME="$PACKAGE Build $CI_BUILD_NUMBER"
    export BUILD_WORKSPACE=`pwd`
    export BUILD_COMMIT="$CI_COMMIT_ID"
    pip install --upgrade selenium
    pip install --upgrade requests

    echo 
    echo
    echo "Running package_upload.py"
    echo
    python $CUMULUSCI_PATH/ci/package_upload.py
    if [ $? != 0 ]; then exit 1; fi
 
    # Test beta
    echo
    echo "-----------------------------------------------------------------"
    echo "ant deployManagedBeta - Install beta and test in beta org"
    echo "-----------------------------------------------------------------"
    echo
    export SF_USERNAME=$SF_USERNAME_BETA
    export SF_PASSWORD=$SF_PASSWORD_BETA
    export SF_SERVERURL=$SF_SERVERURL_BETA
    echo "Got org credentials for beta org from env"
    export PACKAGE_VERSION=`grep PACKAGE_VERSION package.properties | sed -e 's/PACKAGE_VERSION=//g'`
    echo "Attempting install of $PACKAGE_VERSION"
    tries=0
    ant_status=0
    while [ $tries -lt 5 ]; do
        tries=$[tries + 1]
        echo
        echo "-----------------------------------------------------------------"
        echo "ant deployManagedBeta - Attempt $tries of 5"
        echo "-----------------------------------------------------------------"
        echo
        runAntTarget deployManagedBeta
        ant_status=$?
        if [ $ant_status == 0 ]; then
            break
        fi
    done
    if [ $ant_status != 0 ]; then exit 1; fi

    echo
    echo "-----------------------------------------------------------------"
    echo "ant runAllTests: Testing $PACKAGE_VERSION in beta org"
    echo "-----------------------------------------------------------------"
    echo
    runAntTarget runAllTests
    if [ $ant_status != 0 ]; then exit 1; fi
    
    if [ "$GITHUB_USERNAME" != "" ]; then   
        # Create GitHub Release
        echo
        echo "-----------------------------------------------------------------"
        echo "Creating GitHub Release $PACKAGE_VERSION"
        echo "-----------------------------------------------------------------"
        echo
        python $CUMULUSCI_PATH/ci/github/create_release.py

        # Add release notes
        echo
        echo "-----------------------------------------------------------------"
        echo "Generating Release Notes for $PACKAGE_VERSION"
        echo "-----------------------------------------------------------------"
        echo
        # We previously had this script install githubpy instead of PyGithub
        # cleanup in case githubpy is still around.  FIXME: Remove this
        pip uninstall -y githubpy
        pip install --upgrade PyGithub==1.25.1
        export CURRENT_REL_TAG=`grep CURRENT_REL_TAG release.properties | sed -e 's/CURRENT_REL_TAG=//g'`
        python $CUMULUSCI_PATH/ci/github/release_notes.py
    
    
        # Merge master commit to all open feature branches
        echo
        echo "-----------------------------------------------------------------"
        echo "Merge commit to all open feature branches"
        echo "-----------------------------------------------------------------"
        echo
        python $CUMULUSCI_PATH/ci/github/merge_master_to_feature.py
    else
        echo
        echo "-----------------------------------------------------------------"
        echo "Skipping GitHub Releaseand master to feature merge because the"
        echo "environment variable GITHUB_USERNAME is not configured."
        echo "-----------------------------------------------------------------"
        echo
    fi

    # If environment variables are configured for mrbelvedere, publish the beta
    if [ "$MRBELVEDERE_BASE_URL" != "" ]; then
        echo
        echo "-----------------------------------------------------------------"
        echo "Publishing $PACKAGE_VERSION to mrbelvedere installer"
        echo "-----------------------------------------------------------------"
        echo
        export NAMESPACE=`grep 'cumulusci.package.namespace *=' | sed -e 's/cumulusci\.package\.namespace *= *//g'`
        export PROPERTIES_PATH='version.properties'
        export BETA='true'
        echo "Checking out $CURRENT_REL_TAG"
        git checkout $CURRENT_REL_TAG
        python mrbelvedere_update_dependencies.py
    fi
    

# Feature branch commit, build and test in local unmanaged package
elif [ $BUILD_TYPE == "feature" ]; then
    
    # Get org credentials from env
    export SF_USERNAME=$SF_USERNAME_FEATURE
    export SF_PASSWORD=$SF_PASSWORD_FEATURE
    export SF_SERVERURL=$SF_SERVERURL_FEATURE
    
    echo "Got org credentials for feature org from env"
    
    # Deploy to feature org
    echo "Running ant deployCI"
    runAntTarget deployCI
    if [ $? != 0 ]; then exit 1; fi

# Beta tag build, do nothing
elif [ $BUILD_TYPE == "beta" ]; then
    echo
    echo "-----------------------------------------------------------------"
    echo "Nothing to do for a beta tag"
    echo "-----------------------------------------------------------------"
    echo

# Prod tag build, deploy and test in packaging org
elif [ $BUILD_TYPE == "release" ]; then
    echo
    echo "-----------------------------------------------------------------"
    echo "ant deployCIPackageOrg: Deploy release tag to packaging org"
    echo "-----------------------------------------------------------------"
    echo
    # Get org credentials from env
    export SF_USERNAME=$SF_USERNAME_PACKAGING
    export SF_PASSWORD=$SF_PASSWORD_PACKAGING
    export SF_SERVERURL=$SF_SERVERURL_PACKAGING
    
    echo "Got org credentials for packaging org from env"
    
    # Deploy to packaging org
    runAntTarget deployCIPackageOrg
    if [ $? != 0 ]; then exit 1; fi
fi
