===============================
CumulusCI
===============================

.. image:: https://img.shields.io/pypi/v/cumulusci
           :target: https://pypi.org/project/cumulusci/
           :alt: PyPI
.. image:: https://img.shields.io/pypi/pyversions/cumulusci
           :alt: PyPI - Python Version
.. image:: https://img.shields.io/pypi/l/cumulusci
           :alt: PyPI - License
.. image:: https://readthedocs.org/projects/cumulusci/badge/?version=latest
           :target: https://cumulusci.readthedocs.io/en/latest/?badge=latest
           :alt: Documentation Status

CumulusCI is a command line tool belt and set of reusable Python classes useful in the development and release process of building a Salesforce Managed Package application.


Key Features
------------

* Out of the box, CumulusCI provides a complete best practice development and release process based on the processes used by Salesforce.org to build and release managed packages to thousands of users
* Flexible and pluggable system for running tasks (single actions) and flows (sequences of tasks)
* OAuth based org keychain allowing easy connection to Salesforce orgs and stored in local files using AES encryption

For more information, read the `full documentation`_.

.. _`full documentation`: https://cumulusci.readthedocs.io/en/latest/

If you just want a quick intro, watch this screencast demo of using CumulusCI to configure a Salesforce project from a GitHub repository:
https://asciinema.org/a/91555

CumulusCI 1.0 (Ant based) Users, **PLEASE READ**
================================================

The master branch now contains CumulusCI 2 which is not backwards compatible with the previous CumulusCI that was based on Ant. If you are using the Ant targets, please switch to using the `legacy-1.0` branch of the repository which contains the Ant based version. Or, consider upgrading to CumulusCI 2.
