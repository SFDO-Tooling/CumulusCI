Introduction
============

CumulusCI helps development teams build great applications on the Salesforce platform by automating org setup, testing, and deployment.
Automation and Product Delivery with CumulusCI
--------

If your product development lifecycle and release process is anything like ours at Salesforce.org, it's complex. You're managing multiple packages, dependencies, orgs, and release versions. Not to mention managing org metadata and all the setup operations that need to run in the right sequence, before or after a package is installed, to create a properly configured org. 

Consider the example of Nonprofit Success Pack (NPSP), one of Salesforce.org's flagship open source products. NPSP is a large, complex, heterogeneous application. It consists of six managed packages, with complex dependency relationships. Using automation, we deploy all five dependent packages in the right sequence, deliver the unpackaged record types for the Account and Opportunity objects, and perform final configurations to make the customer's experience better, like setting up Global Actions and delivering translations. We deliver biweekly NPSP releases to tens of thousands of customer orgs–with the proper configurations and without requiring end users to work through a lengthy setup guide.

The CumulusCI suite of tools is part of the not-so-secret sauce that makes it possible for us to build and release products. We run CumulusCI automation throughout our development lifecycle, starting from feature branches all the way through delivery of the latest release. 

* GitHub repositories serve as our version-controlled source repositories.
* The CumulusCI command-line interface, CCI, lets us run single-action tasks and multiple-action flows for development and testing.
* MetaCI uses CumulusCI flows to build Salesforce managed packages from GitHub repositories.
* MetaDeploy automates setup and configuration of customer orgs.

**Best practices, proven at scale.** CumulusCI provides a complete development and release process created by Salesforce.org to build and release applications to thousands of users on the Salesforce platform. It's easy to start with the default tasks (single actions) and flows (sequences of actions), or customize by adding your own.

You can use the very same automation that we use internally to quickly:

* Build sophisticated orgs with dependencies automatically installed.
* Load and capture sample datasets to make your orgs feel real.
* Apply transformations to existing metadata to tailor orgs to your specific requirements.
* Run builds in continuous integration systems.
* Create end-to-end browser tests and set up automation using `Robot Framework <https://robotframework.org/>`_.

The automation defined using CumulusCI is portable. It's stored in a source repository and can be run from your local command line, from a continuous integration system, or from a customer-facing installer. CumulusCI can run automation on scratch orgs created using the Salesforce CLI, or on persistent orgs like sandboxes, production orgs, and Developer Edition orgs.

Finally, by way of introduction, CumulusCI is more than just a set of tools. It represents our holistic approach to product development. Rather than focusing on just the org (the [org development model](https://trailhead.salesforce.com/en/content/learn/modules/org-development-model)) or on the package (the [package development model](https://trailhead.salesforce.com/en/content/learn/modules/sfdx_dev_model)),  Salesforce.org has implemented its own _product delivery model_ using CumulusCI. It helps us focus on the customer experience, while also paying attention to technical considerations, such as whether an individual component is best distributed within a package, or as additional unpackaged metadata, or as setup automation that runs before or after a package is installed.

No matter how much complexity you're managing in your development lifecycle, we invite you to see how you can enhance customers' experience of your products using CumulusCI.
Anyone Can Use CumulusCI
--------
Salesforce.org uses CumulusCI to develop products for our nonprofit and education constituents–both public, open source products like NPSP, and commercial managed package products that are developed in private GitHub repositories. But anyone developing on the Salesforce platform can use CumulusCI. It's generic tooling that supports both open source and private development.

Automation defined using CumulusCI can support all roles on a project.

* *Developers* can create new development environments for different feature branches.
* *Quality engineers* can create test environments from feature branches and managed package installs.
* *Doc writers* can create environments to interact with new features and capture screenshots to prepare documentation.
* *Product managers* can create environments to interact with new features and provide feedback on future work.
* *Release engineers* can create beta and final releases and push them to subscriber orgs.
* *Partners* can create their own project which builds on top of your package.
* *Customers* can install the product and get set up using the same automation steps used during development and QA.


Tutorial
--------

For a tutorial introduction to CumulusCI, complete the `Build Applications with CumulusCI <https://trailhead.salesforce.com/en/content/learn/trails/build-applications-with-cumulusci>`_ trail on Trailhead. This trail walks through an example of using CumulusCI to build an extensible app for food banks.


Demos
-----

Watch the following screencasts to get an idea of how to use CumulusCI from a command line.

.. raw:: html

      <!-- https://stackoverflow.com/a/58399508/113477 -->
    <link rel="stylesheet"
        type="text/css"
        href="https://cdnjs.cloudflare.com/ajax/libs/asciinema-player/2.4.1/asciinema-player.min.css" />
    <script src="https://cdn.jsdelivr.net/npm/asciinema-player@2.6.1/resources/public/js/asciinema-player.min.js"></script>

The first screencast shows how to initialize a fresh CumulusCI project:

.. raw:: html

    <asciinema-player preload="True" poster="npt:0:01" src="https://raw.githubusercontent.com/SFDO-Tooling/cci-demo-animations/master/build/1_setup.cast"></asciinema-player>

The next one shows how to use CumulusCI to retrieve metadata from a Salesforce org and save it in GitHub.

.. raw:: html

    <asciinema-player preload="True" poster="npt:0:01" src="https://raw.githubusercontent.com/SFDO-Tooling/cci-demo-animations/master/build/2_retrieve_changes.cast"></asciinema-player>

Manage sample or test data.

.. raw:: html

    <asciinema-player preload="True" poster="npt:0:01" src="https://raw.githubusercontent.com/SFDO-Tooling/cci-demo-animations/master/build/3_populate_data.cast"></asciinema-player>

Customize flows and use CumulusCI for QA.

.. raw:: html

    <asciinema-player preload="True" poster="npt:0:01" src="https://raw.githubusercontent.com/SFDO-Tooling/cci-demo-animations/master/build/4_qa_org.cast"></asciinema-player>

For a narrated demo, see Jason Lantz's `PyCon 2020 presentation <https://www.youtube.com/watch?v=XL77lRTVF3g>`_ (00:36 through 00:54).


Common Misconceptions
---------------------

Why is it called CumulusCI?
  CumulusCI was originally created to power continuous integration (CI) for Cumulus, which was the code name for Salesforce.org's Nonprofit Success Pack. These days, it is used for many projects and supports activities beyond just CI, but the name has stuck.

Is CumulusCI hard to install?
  No. If you already have the Salesforce CLI installed and configured, installing CumulusCI for use across any project is a one-time process that takes 5-10 minutes.

Is CumulusCI specific to Salesforce.org or the nonprofit and education verticals?
  No. It is generic tooling and we aim to provide a best-practice process for anyone doing development on the Salesforce platform.

Is CumulusCI only for Open Source projects?
  No. Salesforce.org uses CumulusCI for both free, public Open Source products and for commercial managed package products developed in private GitHub repositories.

Is CumulusCI a replacement for the Salesforce CLI?
  No. CumulusCI builds on top of the commands provided by the Salesforce CLI and helps to manage and orchestrate them into a simple and straightforward user experience. CumulusCI prescribes a complete development, test, and release process out-of-the-box, while the Salesforce CLI is a lower level toolbelt that more agnostic to a particular process.

Does CumulusCI compete with Salesforce DX?
  No. CumulusCI shares a similar philosophy to Salesforce DX: the source of truth for a project should be in a version-controlled repository, and it should be as easy as possible to set up an org from scratch. CumulusCI uses the Salesforce CLI to perform certain operations such as creating scratch orgs, and is an alternative to bash scripts for running sequences of Salesforce CLI commands.

Do you need to know Python to use CumulusCI?
  No. While CumulusCI is written in Python, most CumulusCI users don't need to know Python, in the same way that most Salesforce DX users don't need to know Node.js.


What to Do Next
-----------------

(TODO)

Depending on your role, certain aspects of CumulusCI may pertain to you more than others.
Use this section as a guide for which parts of the documentation are most likely to be relevant to you.

For everyone
^^^^^^^^^^^^

Developers
^^^^^^^^^^
    * Tutorial

Quality Engineers
^^^^^^^^^^^^^^^^^
Text here.

Product Managers
^^^^^^^^^^^^^^^^
Text here.

Doc Writers
^^^^^^^^^^^
    * :doc:`Automated Release Notes`
    * Parent/Child branch name stuff

Release Engineers
^^^^^^^^^^^^^^^^^
Text here.
