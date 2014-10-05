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
    echo "BUILD FAILED: Could not determine BUILD_TYPE for $CI_BRANCH"
    exit 1
fi

echo "Building $CI_BRANCH as a $BUILD_TYPE build"

# Function to filter out unneeded ant output from builds
function runAntTarget {
    ant $1
    # | \
    #    grep -v '^  *\[delete\]' | \
    #    grep -v '^  *\[copy\]' | \
    #    grep -v '^  *\[loadfile\]' | \
    #    grep -v '^  *\[xslt\]'
}

#---------------------------------
# Run the build for the build type
#---------------------------------

# Master branch commit, build and test a beta managed package
if [ $BUILD_TYPE == "master" ]; then

    # Get org credentials from env
    export SF_USERNAME=$SF_USERNAME_PACKAGING
    export SF_PASSWORD=$SF_PASSWORD_PACKAGING
    export SF_SERVERURL=$SF_SERVERURL_PACKAGING
    
    echo "Got org credentials for packaging org from env"
    
    # Deploy to packaging org
    echo "Running ant deployCIPackageOrg"
    runAntTarget deployCIPackageOrg
    if [ $? != 0 ]; then exit 1; fi
    
    # Upload beta package
    export PACKAGE=`grep cumulusci.package.name.managed cumulusci.properties | sed -e 's/cumulusci.package.name.managed *= *//g'`
    export BUILD_NAME="$PACKAGE Build $CI_BUILD_NUMBER"
    export BUILD_WORKSPACE=`pwd`
    export BUILD_COMMIT="$CI_COMMIT_ID"
    pip install --upgrade selenium
    pip install --upgrade requests
    python $CUMULUSCI_PATH/ci/package_upload.py
    if [ $? != 0 ]; then exit 1; fi
 
    # Test beta
        # Retry if package is unavailable
       
    # Create GitHub Release

    # Add release notes
    
    # Merge master commit to all open feature branches

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
    echo "Nothing to do for a beta tag"

# Prod tag build, deploy and test in packaging org
elif [ $BUILD_TYPE == "release" ]; then
    
    # Get org credentials from env
    export SF_USERNAME=$SF_USERNAME_PACKAGING
    export SF_PASSWORD=$SF_PASSWORD_PACKAGING
    export SF_SERVERURL=$SF_SERVERURL_PACKAGING
    
    echo "Got org credentials for packaging org from env"
    
    # Deploy to packaging org
    echo "Running ant deployCIPackageOrg"
    runAntTarget deployCIPackageOrg
    if [ $? != 0 ]; then exit 1; fi
    
fi
