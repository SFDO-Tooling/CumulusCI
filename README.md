# Clariti CumulusCI

[![PyPI](https://img.shields.io/pypi/v/clariti-cumulusci)](https://pypi.org/project/clariti-cumulusci/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/clariti-cumulusci)
![PyPI - License](https://img.shields.io/pypi/l/clariti-cumulusci)
[![GitHub Actions](https://github.com/ClaritiSoftware/CumulusCI/actions/workflows/feature_test.yml/badge.svg)](https://github.com/ClaritiSoftware/CumulusCI/actions)

> **This is a fork of [CumulusCI](https://github.com/SFDO-Tooling/CumulusCI) maintained by [Clariti Cloud Inc.](https://claritisoftware.com)**
>
> We maintain this fork to provide faster bug fixes, enhanced features, and better support for our internal development workflows. Contributions from the community are welcome!

CumulusCI helps build great applications on the Salesforce platform by
automating org setup, testing, and deployment for everyone --- from
developers and admins to testers and product managers.

**Best practices, proven at scale.** CumulusCI provides a complete
development and release process created by Salesforce.org to build and
release applications to thousands of users on the Salesforce platform.
It\'s easy to start new projects with a standard set of tasks (single
actions) and flows (sequences of tasks), or customize by adding your
own.

**Batteries included.** Out-of-the-box features help you quickly:

-   Build sophisticated orgs with automatic installation of
    dependencies.
-   Load and capture sample datasets to make your orgs feel real.
-   Apply transformations to existing metadata to tailor orgs to your
    specific requirements.
-   Run builds in continuous integration systems.
-   Create end-to-end browser tests and setup automation using [Robot
    Framework](https://claritisoftware.github.io/CumulusCI/robotframework.html).
-   Generate synthetic data on any scale, from a single record to a
    million, using
    [Snowfakery](https://claritisoftware.github.io/CumulusCI/cookbook.html#large-volume-data-synthesis-with-snowfakery).

**Build anywhere.** Automation defined using CumulusCI is portable. It
is stored in a source repository and can be run from your local command
line, from a continuous integration system, or from a customer-facing
MetaDeploy installer. CumulusCI can run automation on scratch orgs
created using the Salesforce CLI, or on persistent orgs like sandboxes,
production orgs, and Developer Edition orgs.

## Installation

```bash
pip install clariti-cumulusci
```

Or using pipx for isolated installation:

```bash
pipx install clariti-cumulusci
```

## Learn more

For a tutorial introduction to CumulusCI, complete the [Build
Applications with
CumulusCI](https://trailhead.salesforce.com/en/content/learn/trails/build-applications-with-cumulusci)
trail on Trailhead.

To go in depth, read the [full
documentation](https://claritisoftware.github.io/CumulusCI/).

If you just want a quick intro, watch [these screencast
demos](https://claritisoftware.github.io/CumulusCI/demos.html) of using
CumulusCI to configure a Salesforce project from a GitHub repository.

For a live demo with voiceover, please see Jason Lantz\'s [PyCon 2020
presentation](https://www.youtube.com/watch?v=XL77lRTVF3g) from minute
36 through minute 54.

## Questions?

- For Clariti CumulusCI specific issues: [Open an issue](https://github.com/ClaritiSoftware/CumulusCI/issues)
- For general CumulusCI questions: Ask in the [CumulusCI (CCI) group in the Trailblazer
Community](https://success.salesforce.com/_ui/core/chatter/groups/GroupProfilePage?g=0F9300000009M9ZCAU)

_Please note:_ This fork is distributed under the [BSD 3-Clause
license](https://github.com/ClaritiSoftware/CumulusCI/blob/main/LICENSE)
and is not covered by the Salesforce Master Subscription Agreement.

<!-- Changelog -->
