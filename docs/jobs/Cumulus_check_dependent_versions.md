# Job: Cumulus_check_dependent_versions

## Overview

This job runs the scripts/set_dependent_versions.py script against every commit to the repository to make sure the script finds no files in need of modification.  If the script finds changes, the build fails and notified the developer.

## Target Org

This job just runs a Python script against the repository code so no org is needed.

## Configuration

### Source Code Management

### Build Environment

### Triggers

### Build

### Post Build

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/Cumulus_check_dependent_versions.png)
