# Job: Cumulus_dev_to_feature

## Overview

This job runs after the Cumulus_dev, Cumulus_dev_cinnamon_deploy, and Cumulus_dev_cinnamon_test jobs all pass build.  It merges all changes from the dev branch back into all feature branches (signified by the feature/ prefix in the branch name).  If the automatic merge fails due to a merge conflict, a Pull Request is created in GitHub to merge dev back into the feature branch.  It is then the developer's responsibility to manually resolve the merge conflict and push the merged code back to their feature branch in GitHub which will automatically close the Pull Request.

## Target Org

This job runs a python script which interacts directly with the GitHub API.  Thus, no target org is needed.

## Configuration

### Title and Description

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_to_feature-title.png)

### Source Code Management

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_to_feature-scm.png)

### Build Environment

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_to_feature-build_environment.png)

### Triggers

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_to_feature-triggers.png)

### Build

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_to_feature-build.png)

### Post Build

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_to_feature-post_build.png)
