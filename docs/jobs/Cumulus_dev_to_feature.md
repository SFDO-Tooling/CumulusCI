# Job: Cumulus_dev_to_feature
[See it in action](http://ci.salesforcefoundation.org/view/feature)

## Overview

This job runs after the [Cumulus_dev](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev.md) job passes build.  It merges all changes from the `dev` branch back into all feature branches (signified by the feature/ prefix in the branch name).  If the automatic merge fails due to a merge conflict, a Pull Request is created in GitHub to merge `dev` back into the feature branch.  It is then the developer's responsibility to manually resolve the merge conflict and push the merged code back to their feature branch in GitHub which will automatically close the Pull Request.

## Target Org

This job runs a python script which interacts directly with the GitHub API.  Thus, no target org is needed.

## Configuration

### Source Code Management

This job runs agains the `dev` branch in the repository.

### Build Environment

We need to pass the GitHub credentials to the script which we do using environment variables including a masked password field.  This should be the same credentials you created when setting up the GitHub Web Hook section in [CumulusCI - Installation and Setup](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/setup/README.md).

### Triggers

Once the [Cumulus_dev](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev.md) build passes, it triggers this job to build.  This ensures the latest merge is good before pushing it out to all feature branches, a rather intrusive operation.

### Build

The Build uses a custom shell script which activates the python virtual environment containing the PyGithub package for talking to GitHub.  Then, we execute the script.

![Cumulus_dev_to_feature - Config](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/Cumulus_dev_to_feature.png)

### Post Build

The Editable Email Notification post build action is used to send a formatted email to the release manager on failure (Failure) and recovery (Fixed).
