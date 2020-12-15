Key Concepts
============

Key concept. Developer jargon. 10-cent words that sound like a technical writer patting himself on the back. (Hi there!) We imagine your cursor subconsciously drifting its way to the hyperlink for the next chapter already. BUT in an effort to give you the tools to build and test customized features with CumulusCI, it's only right that we demystify the process by explaining the *how* and the *why* in order to help you achieve your goal of seamless automation.

Don't worry, we'll make this as painless as possible.

Packages
--------

If you've come this far in your search of customization, we're guessing you're familiar with packages as well as their role in customizing a Salesforce org. However, because most everything that is built in CumulusCI is deployed via packages, it's essential to clarify once more:

A **package** is a container for something as small as an individual component or as large as a set of related apps. After creating a package, you can distribute it to other Salesforce users and organizations, including those outside your company.

**Unmanaged packages** are typically used to distribute open-source (non-proprietary) features or application templates to provide developers with the basic building blocks for an application. Once the components are installed from an unmanaged package into a specific org, it's what's known as an org implementation. These freshly installed components can be edited as seen fit by the owners of this implementation. The developer who created and uploaded the unmanaged package has no control over the installed components, and can't change or upgrade them.
 
**Managed packages** are typically used by Salesforce partners to distribute and sell applications to customers. They are proprietary code that can only be upgraded and deployed by the developer that built them. To ensure seamless upgrades, certain destructive changes, like removing objects or fields, cannot be performed.

Packages are also built, stored and deployed via **projects**.

Projects
--------

When you work with CumulusCI, you do so inside a project. A project is an individual git repository (think GitHub) that contains Salesforce metadata as well as the CumulusCI automation (e.g., tasks and flows) that builds and releases the project. Most importantly, a project can build one - and only one(!) - package in its repository. This one-to-one relationship between project and package is what allows version control to track any changes your team made to the repository with minimal collision.

It's important to note that a project may not even contain a package; for example, it can be built to deliver functionality to records, or test data for QA. A project may constitute the entirety of a product made for release, or may be one of multiple projects banded together to make a product (think NPSP). Basically, whatever feature in your product that needs specialized Salesforce metadata and CumulusCI automation in order to be built and deployed, *especially* packages (we cannot stress this enough!), requires its own unique project. 

Project Structure
-----------------

Keychain
^^^^^^^^

Each project comes with a Salesforce CLI keychain, a unique identifier of characters to separate a project and its files from any other. This deters collisions with another org. (Example: Most projects contain a "dev" org. While the name is ubiquitous across Salesforce orgs, the keychain attached is what makes it unique.) 

Project Directory
^^^^^^^^^^^^^^^^^

The root directory of your CumulusCI project. Because each project is linked to a single GitHub repository, you can always be confident of the scope of the actions you're taking. And thanks to the keychain, CumulusCI knows which project you are working on by the current working directory of your shell. 

[NOTE: Save yourself a headache by making sure you're in the correct repository for your project before running project-specific commands; otherwise, your project will produce an error. (This tends to be one of the biggest troubleshooting issues that developers run into with CumulusCI. Check for this first and you might save yourself an extra trip to this guide.)]

In order to be used as a CumulusCI project, a directory must both be a Git repository and contain a ``cumulusci.yml`` configuration file. We'll show you how to get set up with a new or existing CumulusCI project in the [TODO link Get Started section].

cumulusci.yml
^^^^^^^^^^^^^

The ``cumulusci.yml`` file defines a project's automation in CumulusCI. It contains all the customizations and configurations that pertain to your project's lifecycle. It can encompass everything from customizing the shapes of scratch orgs to configuring tasks and flows.

Learn more about customizing CumulusCI automation in the [TODO: link Customization section].

force-app (or src)
^^^^^^^^^^^^^^^^^^

The main body of the project's code and metadata lives in the ``force-app`` directory for Salesforce DX-format projects and ``src`` for Metadata API-format projects. For managed package projects, only this metadata is part of the package. Projects have the vast majority of their components stored here.

orgs Directory
^^^^^^^^^^^^^^

The ``.json`` files found in the ``orgs`` directory define the Salesforce DX org configurations that are available to the project. We cover scratch org management in depth in [TODO: link Scratch Org Management].

datasets
^^^^^^^^

Each project may have one or more **datasets**: on-disk representations of record data that can be inserted into Salesforce orgs, and which can also be modified and re-captured during the evolution of the project. Datasets are stored in the ``datasets`` directory. Learn more about datasets in [TODO: link Automating Data Operations].

Robot
^^^^^

Robot Framework provides browser automation for end-to-end testing. Each project contains a ``robot`` directory, which stores the resources and test suites for the project's Robot Framework test suites. New CumulusCI projects start with a simple Robot test case that creates a Contact record.

While Robot Framework is used primarily for browser automation testing, it can also be harnessed to help configure orgs where other strategies and APIs are insufficient. [TODO LINK TO EXPLAIN THIS FURTHER?]

unpackaged metadata
^^^^^^^^^^^^^^^^^^^

A product doesn't just encompass the contents of a managed package or a single deployment. It also includes **unpackaged metadata**: extra bundles of Salesforce metadata that further tailor an org or complete the product.

In a CumulusCI project, all unpackaged metadata is stored in subdirectories within the ``unpackaged`` directory. Unpackaged metadata plays multiple roles, including preparing an org for installing packages, adding more customization after the package or application is deployed, and customizing specific orgs that are used in the product's development process.

Learn more about managing unpackaged metadata in [TODO: link Managing unpackaged configuration].

Project Orgs & Services
-----------------------

Orgs and services are external, authenticated resources that each project uses. CumulusCI makes it easy to connect orgs, as well as services like GitHub or MetaDeploy, to a single project, or to use them across many projects.

Each project has its own set of orgs, including active scratch orgs, persistent orgs like a production or packaging org, and predefined scratch org configurations. CumulusCI securely stores org authentication information in its keychain, making it easy to access connected orgs at any time. The ``cci org list`` command shows all of the orgs connected to a project. Orgs can also be shared across multiple projects.

Configuring orgs in CumulusCI is powerful, but comes with some complexity. To review the details, read the sections [TODO: link Scratch org environments] and [TODO: link persistent org section].

Services are usually, but not always, connected to CumulusCI across projects as part of the global keychain. The ``command cci service`` list shows you which services are connected in the context of the current project.

Services can be connected at the project level, which means that they're scoped to a single project and cannot be shared. Global services are easy to use and share and, therefore, we recommend you rely on them for the most part. However, when you encounter a scenario where, for example, you need to use a specific Dev Hub for one - and only one(!) - project, you can simply connect to that service by way of the ``cci service connect devhub --project`` command.

Tasks and Flows
---------------

CumulusCI uses a framework of **tasks** and **flows** to organize the automation that is available to each project.

Tasks are units of automation. A task could perform a deployment, load a dataset, retrieve material from an org, install a managed package, or undertake many other activities. CumulusCI ships with scores of tasks out of the box.

You can review the tasks available in a project by running ``cci task list``; learn more about a task and how to configure its options with ``cci task info <name>``, where ``<name>`` is the name of the task; and run a task with ``cci task run <name> --org <org>``, where ``<name>`` is the name of the task and ``<org>`` is the org you'd like to run it against. For example, the ``run_tests`` task executes Apex unit tests. If you have an org called ``dev``, you can run this task against this org with the command ``cci task run run_tests --org dev``.

Many operations that you'll undertake with CumulusCI, including creating new orgs, use flows. Flows are ordered sequences of tasks (and other flows!) that produce a cohesive outcome, such as an org that's configured to suit a specific workflow.

Find the list of flows available in a project by running ``cci flow list``. Learn more about a flow and the tasks it contains with ``cci flow info <name>``, where ``<name>`` is the name of the flow, and run a flow with ``cci flow run <name> --org <org>``, where ``<name>`` is the name of the flow and ``<org>`` is the org you'd like to run it against.

Many of the most common flows you'll work with in CumulusCI are designed to build and configure specific orgs for you. Here's a few of the most common flows that build orgs:

* ``dev_org``: This is an unmanaged org that is designed for development use. This flow is typically used with an org whose configuration is ``dev`` or ``dev_namespaced``.
* ``qa_org``: This is an unmanaged org that is designed for testing. This flow is typically used with an org whose configuration is ``qa``.
* ``install_beta``: This is a managed org with the latest beta release installed, for projects that build managed packages. This flow is typically used with an org whose configuration is ``beta``.
* ``install_prod``: This is a managed org with the latest release installed, for projects that build managed packages.
* ``regression_org``: This is a managed org that starts with the latest release installed and is then upgraded to the latest beta to simulate a subscriber upgrade for projects that build managed packages. This flow is typically used with an org whose configuration is ``release``.

CumulusCI derives the library of flows and tasks available for any project by combining its internal standard library with your customizations in ``cumulusci.yml``. Customizations can add new tasks and flows, customize the way featured tasks behave, and extend, combine, and modify featured flows to suit the specific needs of the project. We cover customization in depth in [TODO: reference Customizing CumulusCI].
