=========
CumulusCI
=========

|coverage| |pypi| |python| |license| |docs|

.. |coverage| image:: https://coveralls.io/repos/github/SFDO-Tooling/CumulusCI/badge.svg?branch=main
              :target: https://coveralls.io/github/SFDO-Tooling/CumulusCI?branch=main
              :alt: Code Coverage
.. |pypi| image:: https://img.shields.io/pypi/v/cumulusci
           :target: https://pypi.org/project/cumulusci/
           :alt: PyPI
.. |python| image:: https://img.shields.io/pypi/pyversions/cumulusci
           :alt: PyPI - Python Version
.. |license| image:: https://img.shields.io/pypi/l/cumulusci
           :alt: PyPI - License
.. |docs| image:: https://readthedocs.org/projects/cumulusci/badge/?version=latest
           :target: https://cumulusci.readthedocs.io/en/latest/?badge=latest
           :alt: Documentation Status

CumulusCI helps build great applications on the Salesforce platform by automating org setup, testing, and deployment for everyone — from developers and admins to testers and product managers.

**Best practices, proven at scale.** CumulusCI provides a complete development and release process created by Salesforce.org to build and release applications to thousands of users on the Salesforce platform. It's easy to start new projects with a standard set of tasks (single actions) and flows (sequences of tasks), or customize by adding your own.

**Batteries included.** Out-of-the-box features help you quickly:

* Build sophisticated orgs with automatic installation of dependencies.
* Load and capture sample datasets to make your orgs feel real.
* Apply transformations to existing metadata to tailor orgs to your specific requirements.
* Run builds in continuous integration systems.
* Create end-to-end browser tests and setup automation using `Robot Framework <https://cumulusci.readthedocs.io/en/latest/robotframework.html>`_.
* Generate synthetic data on any scale, from a single record to a million, using `Snowfakery <https://cumulusci.readthedocs.io/en/latest/cookbook.html#large-volume-data-synthesis-with-snowfakery>`__.

**Build anywhere.** Automation defined using CumulusCI is portable. It is stored in a source repository and can be run from your local command line, from a continuous integration system, or from a customer-facing MetaDeploy installer. CumulusCI can run automation on scratch orgs created using the Salesforce CLI, or on persistent orgs like sandboxes, production orgs, and Developer Edition orgs.

Learn more
----------

For a tutorial introduction to CumulusCI, complete the `Build Applications with CumulusCI <https://trailhead.salesforce.com/en/content/learn/trails/build-applications-with-cumulusci>`_ trail on Trailhead.

To go in depth, read the `full documentation <https://cumulusci.readthedocs.io/en/latest/>`_.

If you just want a quick intro, watch `these screencast demos <https://cumulusci.readthedocs.io/en/latest/demos.html>`_ of using CumulusCI to configure a Salesforce project from a GitHub repository.

For a live demo with voiceover, please see Jason Lantz's 
`PyCon 2020 presentation <https://www.youtube.com/watch?v=XL77lRTVF3g>`_
from minute 36 through minute 54.

Questions?
----------

Ask in the `CumulusCI group in the Trailblazer Community <https://success.salesforce.com/_ui/core/chatter/groups/GroupProfilePage?g=0F9300000009M9ZCAU>`_.

*Please note:* CumulusCI is distributed under an `open source license <https://github.com/SFDO-Tooling/CumulusCI/blob/main/LICENSE>`_ and is not covered by the Salesforce Master Subscription Agreement.
