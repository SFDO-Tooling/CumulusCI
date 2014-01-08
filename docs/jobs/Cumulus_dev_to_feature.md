# Job: Cumulus_dev_to_feature

## Overview

This job runs after the Cumulus_dev, Cumulus_dev_cinnamon_deploy, and Cumulus_dev_cinnamon_test jobs all pass build.  It merges all changes from the dev branch back into all feature branches (signified by the feature/ prefix in the branch name).  If the automatic merge fails due to a merge conflict, a Pull Request is created in GitHub to merge dev back into the feature branch.  It is then the developer's responsibility to manually resolve the merge conflict and push the merged code back to their feature branch in GitHub which will automatically close the Pull Request.

## Target Org

This job runs a python script which interacts directly with the GitHub API.  Thus, no target org is needed.

## Configuration

### Title and Description

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_to_feature-title.png)

### Source Code Management

This job runs agains the dev branch in the repository.

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_to_feature-scm.png)

### Build Environment

We need to pass the GitHub credentials to the script which we do using environment variables including a masked password field.  This should be the same credentials you created when setting up the GitHub Web Hook section in [CumulusCI - Installation and Setup](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/setup/README.md).

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_to_feature-build_environment.png)

### Triggers

Since merging code into all open feature branches is a fairly intrusive operation, we don't run this job until after all test builds have passed against the branch.

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_to_feature-triggers.png)

### Build

The Build uses a custom shell script which activates the python virtual environment containing the PyGithub package for talking to GitHub.  Then, we execute the script.

FIXME: Script path should point to CumulusCI/scripts/github/merge_dev_to_feature.py

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_to_feature-build.png)
