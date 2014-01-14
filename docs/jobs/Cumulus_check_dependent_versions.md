# Job: Cumulus_check_dependent_versions
[See it in action](http://ci.salesforcefoundation.org/view/feature)

## Overview

This job runs the scripts/set_dependent_versions.py script against every commit to the repository to make sure the script finds no files in need of modification.  If the script finds changes, the build fails and notified the developer.

## Target Org

This job just runs a Python script against the repository code so no org is needed.

## Configuration

### Source Code Management

We want to test the latest commit in the main Cumulus repository.

### Build Triggers

Build whenever a change is pushed to GitHub.  This triggers after any push to any branch.

### Build

We use a simple script to active the Python virtualenv and run the script redirecting the output to a file.  Then, we check if the string 'Updating' appears at the beginning of any of the script's output lines.  If found, fail the build.

### Post Build

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/Cumulus_check_dependent_versions.png)
