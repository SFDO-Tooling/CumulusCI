# Job: Cumulus_rel

## Overview

This job is triggered by the creation of a tag prefixed with rel/ (i.e. rel/1.2).  It deploys the release tag code to the cumulus.rel org to allow for packaging into a managed package release.

## Target Org

This job runs against the cumulus.rel org which is the package org for Cumulus.

## Configuration

### Title and Description

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_rel-title.png)

### Parameters

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_rel-params.png)

### Source Code Management

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_rel-scm.png)

### Build Environment

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_rel-build_environment.png)

### Triggers

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_rel-triggers.png)

### Build

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_rel-build.png)

### Post Build

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_rel-post_build.png)
