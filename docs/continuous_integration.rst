Continuous Integration
======================

The "CI" in CumulusCI stands for "continuous integration".
Continuous integration is the practice of automatically running a project's tests for any change before merging that change to the ``main`` branch in the repository.
Continuous integration also configures the repository so that changes are merged only if the tests have passed.
This practice keeps the ``main`` branch in an error-free state where it can be released any time.

Teams can create bespoke automation for CumulusCI tailored to their project's needs.
Once created, the automation is available to all project participants, from developers and quality engineers, to documentation writers and product managers.
CumulusCI takes this reuse of automation one step further by letting it run in the context of CI systems like GitHub Actions, CircleCI, or Azure Pipelines.
This consistent reuse of automation from local environments to cloud-based CI systems gives teams the ability to develop, test, and deploy their projects with confidence.



CumulusCI Flow
--------------
CumulusCI Flow is the process by which Salesforce metadata is developed, tested, and deployed to our customers.
It is similar to GitHub Flow, with a few tweaks and additions.

To learn which CumulusCI flows are best designed for creating scratch orgs, running CI builds,
managing the development process, and more, see :doc:`CumulusCI Flow <cumulusci_flow>`.



CumulusCI in GitHub Actions
---------------------------
GitHub Actions specify custom workflows that run directly in your GitHub repository.
These workflows perform a variety of tasks, such as running test suites, performing linting checks on code, and creating code coverage reports.
CumulusCI can also execute flows in GitHub Actions, making it possible to run scratch org builds and execute Apex and Robot Framework test passes leveraging the custom automation defined in ``cumulusci.yml``.

To learn more about these custom workflows, see our `template repository <https://github.com/SFDO-Tooling/CumulusCI-CI-Demo>`_ which is configured to run :doc:`CumulusCI Flow <cumulusci_flow>` using :doc:`GitHub Actions <github_actions>`.



MetaCI
------
Salesforce.org Release Engineering also maintains a continuous integration system called *MetaCI*.
MetaCI is an open source app built to run on Heroku, and is designed specifically to work with CumulusCI and Salesforce.
MetaCI's advantages for CumulusCI-based development processes include:

* Easily configuring CumulusCI flows as CI builds.
* Scaling efficiently up to 100 parallel builds without reserving permanent capacity.
* Exposing CumulusCI flows through a web UI for users to create scratch orgs.

Setting up MetaCI requires experience working with apps on Heroku and CumulusCI.
To learn more about MetaCI and how to run it with a project, see `MetaCI <https://github.com/SFDO-Tooling/MetaCI>`_.
 


Further Reading
---------------

.. toctree::
   :maxdepth: 1

   cumulusci_flow.rst
   2gp_testing.rst
   github_actions.rst


