Introduction
============

.. toctree::

============
Introduction
============
CumulusCI helps teams build great applications on the Salesforce platform by automating org setup, testing, and deployment.

**Best practices, proven at scale.** CumulusCI provides a complete development, test, and release process, created by Salesforce.org, that has undergone over 300,000 production builds (and counting). CumulusCI enables Salesforce.org to build and release applications to tens of thousands of users on the Salesforce platform. It's easy to start with the default tasks (single actions) and flows (sequences of actions), and to customize your own! 

**Portable Automation** Automation defined using CumulusCI is portable, stored in a source repository and can be run from your local command line, from a continuous integration system, or from a customer-facing MetaDeploy installer. CumulusCI can run automation on scratch orgs created using the Salesforce CLI, or on persistent orgs like sandboxes, production orgs, and Developer Edition orgs.

**Tools For Everyone** Automation that helps you do something useful with a Salesforce org to prepare a development or test environment, is likely to benefit many people involved in your project:
    * **Developers** who need to create new development environments for different feature branches
    * **Release Engineers** who need to debug build failures by running the scripts locally
    * **QAs** who need to create test environments from feature branches and managed package installs
    * **Doc Writers** who need to create environments to interact with new features and capture screenshots to prepare documentation for a release
    * **Product Managers** who need to create test environments with new features and releases to provide feedback on feature implementations
    * **Partners** who need to create test and development environments to build on top of your package
    * **Web Apps** you can build to reuse the automation logic (i.e. custom CI app, web based installers, etc

**Batteries included.** Out-of-the-box features help you quickly:
    * Build sophisticated orgs with automatic installation of dependencies.
    * Load and capture sample datasets to make your orgs feel real.
    * Apply transformations to existing metadata to tailor orgs to your specific requirements.
    * Run builds in continuous integration systems.
    * Create end-to-end browser tests and setup automation using Robot Framework.

Learn More
==========

For a tutorial introduction to CumulusCI, complete the `Build Applications with CumulusCI<https://trailhead.salesforce.com/en/content/learn/trails/build-applications-with-cumulusci>`_ trail on Trailhead.

To go in depth, read the `full documentation <https://cumulusci.readthedocs.io/en/latest/>`_.

If you just want a quick intro, watch `these screencast demos <https://cumulusci.readthedocs.io/en/latest/demos.html>`_ of using CumulusCI to configure a Salesforce project from a GitHub repository.

For a live demo with voiceover, please see `Jason Lantz's PyCon 2020 presentation <https://www.youtube.com/watch?v=XL77lRTVF3g>`_ from minute 36 through minute 54.

FAQ
===
Is CumulusCI hard t install?
No. If you already have ``sfdx`` installed and configured, installing and configuring CumulusCI for use across any project is a one time process that takes about 5 minutes. There's even a dedicated `Trailhead Module that covers installing and configuring <https://trailhead.salesforce.com/content/learn/modules/cumulusci-setup?trail_id=build-applications-with-cumulusci>`_ ``sfdx``, VSCode, CumulusCI, and GitHub Desktop (optional).

Is CumulusCI specific to Salesforce.org or the nonprofit and education verticals?
No. It is generic tooling and a best practices based process for anyone doing on-platform development.

Is CumulusCI only fro Open Source projects?
No. Salesforce.org uses Cumulusci for paid managed package products developed in private GitHub repositories.

Is CumulusCI a replacement for Salesforce DX?
No. CumulusCI helps to manage and orchestrate the operations that Salesforce DX provides to create simple and straight forward user experience. CumulusCI prescribes a complete development, test, and release process out-of-the-box, while Salesforce DX is a lower level toolbelt that is process and tooling agnostic.

Does CumulusCI compete with Salesforce DX?
No. CumulusCI is a competitor to bash scripts in the Salesforce DX world and enables its users to more easily adopt and gain value from Salesforce DX

Do you need to know Python to use CumulusCI?
No. While CumulusCI is written in Python, most CumulusCI users don't need to know Python in the same way most Salesforce DX users don't need to know Node.js.

Is CumulusCI ant based?
No. Some internal teams and external users first encountered “CumulusCI” as a collection of Ant scripts created years ago.  CumulusCI Suite started as a refactoring of the processes from those early Ant scripts that has evolved substantially over the last 4 years. 


What To Read Next
=================
Depending on your role, certain aspects of CumulusCI may pertain to you more than others.

Developers
----------
    * Tutorial

Release Engineers
-----------------
Text here.

Product Managers
----------------
Text here.

Quality Engineers
-----------------
Text here.

Doc Writers
-----------
    * :doc:`Automated Release Notes`
    * Parent/Child branch name stuff