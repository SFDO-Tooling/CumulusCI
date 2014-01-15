# Job: Cumulus_uat_managed
[See it in action](http://ci.salesforcefoundation.org/view/uat)

## Overview

The Cumulus_uat_managed job deploys the latest managed beta release of Cumulus to the cumulus.uat org dedicated to testing UAT releases.

## Target Org

Runs against the org cumulus.uat which is dedicated for use by this job only.

## Configuration

### Source Code Management

The deployManagedUAT target is branch independent so we just check out the `dev` branch.

### Build Triggers

Use two build triggers:

* A daily scheduled build
* A URLTrigger which polls the [mrbelvedere](http://salesforcefoundation.github.io/mrbelvedere/) application for a change in the latest Cumulus managed beta release and kicks off the build if a change is found.  Since this is polling based, it can take a few minutes after adding the install url to the Release in GitHub for the trigger to kick in.

### Build Environment

Set a custom build name so we know which tag was built rather than just a simple build number.

### Build

The [deployManagedUAT](https://github.com/SalesforceFoundation/CumulusCI/blob/master/README.md#deploymanageduat) target is used to deploy the 5 original NPSP managed packages as well as the latest Cumulus managed beta package.

### Post Build

The Editable Email Notification post build action is used to send a formatted email to the release manager on Failure and Fixed.

![Cumulus_uat_managed - Config](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/Cumulus_uat_managed.png)
