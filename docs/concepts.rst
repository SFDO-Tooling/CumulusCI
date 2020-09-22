Key Concepts
============

The Product Development Model
-----------------------------
CumulusCI extends the concepts of the `Org Development Model <https://trailhead.salesforce.com/en/content/learn/modules/org-development-model>`_ and the `Package Development Model <https://trailhead.salesforce.com/en/content/learn/modules/sfdx_dev_model>`_ to form a new model, which we call the Product Development Model.

In the Product Development Model, a product is composed of one or more managed packages, alongside unpackaged customizations and sophisticated setup automation that runs before or after the delivery of the product’s packaged elements. The Product Development Model focuses on the customer experience, not on the technical artifacts you’re delivering, and focuses on making it possible to deliver a first-class, fully-configured customer experience — no matter how complex the product might be.

CumulusCI automation, which makes it easy to create products that span multiple package repositories and include complex setup operations, is how we implement the Product Development Model, along with MetaDeploy and other applications in the CumulusCI Suite.

The Product Development Model aims to represent a holistic view of delivery of a product instead of simply releasing a package. Here’s a real-world example drawn from Salesforce.org’s product portfolio.

The Nonprofit Success Pack and the Product Development Model
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The Nonprofit Success Pack, or NPSP, is one of Salesforce.org’s flagship products. The NPSP consists of six managed packages, with complex dependency relationships between them, alongside unpackaged metadata and setup automation that helps create a usable NPSP org.

Salesforce.org delivers NPSP using CumulusCI and the Product Development Model because those tools are what make it possible for us to ship this large, complex, heterogeneous application efficiently to tens of thousands of customers — without a lengthy setup guide to be completed by the end user. CumulusCI automation seamlessly deploys all six managed packages in the right sequence, delivers the unpackaged metadata, like Record Types and Page Layouts, we supply to make the customer’s life easier, and executes setup automation like populating NPSP relationship values. 

CumulusCI runs this automation throughout our development lifecycle, starting from feature branches in the hands of our developers and culminating the delivery of new versions of the application to our users, including through MetaDeploy — which runs the very same automation we use internally to set up and configure a customer org.

Throughout the CumulusCI documentation, we’ll have the Product Development Model in mind. 

Projects
--------

When you work with CumulusCI, you do so inside a project. A project is a version control repository that contains Salesforce metadata as well as the CumulusCI automation that builds and releases the project. A project usually has a one-to-one relationship with a managed package, if building a package, or with an org implementation.

CumulusCI scopes many of its activities to the project, so you’ll always run your CumulusCI commands inside your repository directory. Each project gets its own keychain, which we’ll talk about in detail below. Each project has its own set of scratch orgs, which CumulusCI namespaces in the Salesforce DX keychain to prevent collisions. And each project is linked to a single GitHub repository, so you can always be confident of the scope of the actions you’re taking.

CumulusCI knows which project you are working on by the current working directory of your shell. Make sure to change directories inside your project before you run project-specific commands.

Project Structure
-----------------

A CumulusCI project represents an application or a major component of an application on the Salesforce platform. Each project corresponds with a single managed package, or with an org-based implementation. In this documentation, we’ll often speak about a package; if you’re building a project that isn’t packaged, please take this to refer to the unmanaged package within which your implementation is deployed.

Together with the core package, a CumulusCI project encompasses a variety of unpackaged application components, automation, tests, and other support material. This section is intended to review the major components that are common to most CumulusCI projects. Not every project will include every component.

A typical CumulusCI project will have a directory structure that looks like this. Note that not all of these components will be present in a brand-new CumulusCI project. ::

    MyProject/
        cumulusci.yml
        datasets/
            test_data.sql
            mapping.yml
        force-app/
            main/
                default/
                    ... many subfolders ...
        orgs/
            dev.json
            beta.json
            ... others ...
        robot/
            MyProject/
                ... subfolders ...
        sfdx-project.json
        unpackaged/
            pre/
                ... subfolders ...
            post/
                ... subfolders ...
            config/
                ... subfolders ...

If your project uses Metadata API format, you’ll have a src folder instead of force-app. There may be other variations as well, but most projects will have a lot in common with this sketch. Let’s look at each primary component in turn.

``cumulusci.yml``
+++++++++++++

This is the definition of the project’s automation. It includes information about the project itself as well as customizations that define how scratch orgs are built and provide other important functionality to be used as part of the project’s lifecycle.

When you work with CumulusCI in a project, the contents of your cumulusci.yml are merged with the cumulusci.yml that comes with CumulusCI and defines out-of-the-box functionality. From time to time we’ll refer to that as the standard library.

``datasets``
++++++++++++

This folder contains one or more datasets: on-disk representations of record data that can be inserted into Salesforce orgs, and which can also be modified and re-captured during the evolution of the project.

``force-app`` (or ``src``)
++++++++++++++++++++++++++

This is the main body of the project’s code and metadata. The contents of this folder — ``force-app`` for Salesforce DX-format projects and ``src`` for Metadata API-format projects — are what falls within the package. Most projects have the vast majority of their components stored here.

``orgs``
++++++++

The .json files in this directory define the Salesforce DX org configurations that are available to the project, which align with YML markup in ``cumulusci.yml`` that further tailors the configuration. Salesforce DX org configurations are documented in the Salesforce DX Developer Guide. They’re created with the project and generally do not need to be modified on a day-to-day basis. These files define various kinds of org you’ll use in working with the project, including defining settings for the Salesforce features your project needs — like Person Accounts, multicurrency, Chatter, or Enhanced Notes.

``robot``
+++++++++

This folder contains the resources and test suites for the project’s Robot Framework test suites. While Robot Framework is used primarily for browser automation testing, in a small number of situations, Robot Framework may also be harnessed to help configure orgs where other strategies and APIs are insufficient.

``unpackaged``
++++++++++++++

The unpackaged directory contains both unpackaged elements of the application — that is, components that you wish to deliver to end users, but cannot or do not wish to include in the package — and other bundles of metadata that are used operationally during the project’s development to further tailor org and application configuration.

There are three primary subdirectory trees under unpackaged. All of these trees contain metadata bundles in Metadata API format: that is, a directory containing a ``package.xml`` manifest and Metadata API-format source code. CumulusCI does not support Salesforce DX format for unpackaged bundles.

``unpackaged/pre`` contains one or more metadata bundles that are deployed to all orgs before the application code (``force-app``).
``unpackaged/post`` contains one or more metadata bundles that are deployed to all orgs after the application code.
``unpackaged/config`` contains one or more metadata bundles that are only deployed when explicitly configured. Bundles in ``unpackaged/config`` are typically associated with specific deployment tasks. For example, an unpackaged configuration bundle called ``dev`` might be deployed with a task called ``deploy_dev_config``. However, this is a convention, and individual projects may vary.

Bundles in ``unpackaged/config`` are sometimes part of end-user delivery of the application and sometimes are purely for internal consumption.

Managing Orgs & Services with the Keychain
------------------------------------------

CumulusCI gives each project a keychain, and also offers a global keychain that’s shared across projects. The keychain’s role is to store access information for all of the orgs you’re using with the project — both scratch orgs and persistent orgs — and the details of the services you’ve connected, such as a GitHub account or an instance of MetaDeploy.

Services
++++++++

Services are usually, but not always connected to CumulusCI across projects: they live in the global keychain. A service represents functionality external to CumulusCI that you authenticate with in order to achieve a workflow. For example, a GitHub account or MetaDeploy account would be represented by a service.

The command ``cci service list`` shows you which services are connected in the context of the current project.

Some services can be connected at the project level, which means that they’re scoped to a single project and aren’t shared. We recommend primarily using global services because they’re easier to use, but you may encounter scenarios where, for example, you need to use a specific Dev Hub for one and only one project. Connecting that service with ``cci service connect devhub --project`` supports that use case.

CumulusCI stores service authentication details in an encrypted file in your configuration directory.

Orgs
++++

Each project’s keychain stores authentication information for all of the orgs that are in use by the project, including scratch orgs, persistent orgs like a production or packaging org, and information about scratch orgs that are yet to be created.

The ``cci org list`` command shows all of the connected orgs in the project keychain, as well as defined scratch org configurations that have not yet been built. (We’ll talk more about org configurations shortly).

When CumulusCI builds a scratch org, it automatically shares the org with your Salesforce DX keychain, but names the org in a way that helps keep orgs separate between projects. For example, if you build a ``dev`` org in the project ``Test``, CumulusCI will call that org ``dev`` in your CumulusCI keychain, and ``Test__dev`` in the Salesforce DX keychain. This prevents your scratch orgs from colliding across projects.

When you attach a persistent org to a project’s keychain using ``cci org connect``, that org is not added to the Salesforce DX keychain - it belongs to the project alone.

CumulusCI stores org authentication details in an encrypted file in your configuration directory.

Orgs and Org Configurations
---------------------------

There’s a file called ``dev.json`` in orgs. There’s a section called ``orgs:`` in cumulusci.yml. There’s a flow called ``dev_org``. And when I run ``cci org list``, I see ``dev`` in my listing. How do these things all go together?

Let’s start with what makes up an org configuration in CumulusCI: an org configuration is composed of options set in ``cumulusci.yml``, or in the CumulusCI standard library, plus the contents of a specific ``.json`` file in orgs.

These elements come together for a couple of reasons. One is that CumulusCI adds two facets to the org configuration that aren’t part of the underlying Salesforce DX org configuration, which is the ``.json`` file in ``orgs``. Those facets are whether or not the org is namespaced, and how many days the org’s lifespan is. The other reason is that CumulusCI makes it easy for you to build many named orgs that share the same configuration. Let’s look at how that works.

In an out-of-the-box CumulusCI project, you might have a file called orgs/dev.json that looks like this: ::
    {
        "orgName": "Food-Bank-Demo - Dev Org",
        "edition": "Developer",
        "settings": {
            "lightningExperienceSettings": {
                "enableS1DesktopEnabled": true
            },
            "chatterSettings": {
                "enableChatter": true
            }
            /* more JSON configuration follows */
        }
    }

Then, the CumulusCI standard library (note: you won’t see this in your project’s ``cumulusci.yml``, because it’s an out-of-the-box configuration), an ``orgs:`` entry is defined that uses this configuration file: ::

    orgs:
        scratch:
            dev:
                config_file: orgs/dev.json
                days: 7

This tells CumulusCI that we have an org configuration called ``dev``, which is built in Salesforce DX using the ``orgs/dev.json`` configuration file, which has a 7-day lifespan, and which is not namespaced. (If this org were namespaced, we’d have the key ``namespaced: True`` here; it defaults to ``False``).

An org configuration is also a name for an org that you can build by running a flow (we cover running flows in the next section). The flows that you run to build an org often, but not always, have a name that connects to the org configuration. For example, to run the ``dev_org`` flow against an org with the dev configuration, you can just do ::

    $ cci flow run dev_org --org dev

and CumulusCI will build the org for you. The org named ``dev`` has the configuration ``dev``, automatically.

You can create new org names that inherit their configuration from a built-in name. For example, to create a new org name that uses the same configuration as type ``dev``, you can use the command ::

    $ cci org scratch dev new-org

You can then run ::

    $ cci flow run dev_org --org new-org

to build this org, independent of the org dev but sharing its configuration. You can have as many named orgs as you wish, or none at all: many CumulusCI users work only with the built-in org names.

CumulusCI comes with five org configurations, each of which is paired with a preferred flow to build that type of org:

* ``dev`` is for use with the ``dev_org`` flow and uses the ``orgs/dev.json`` configuration file.
* ``qa`` is for use with the ``qa_org`` flow. ``qa`` and ``dev`` are the same out of the box, but can be customized to suit the needs of the project.
* ``feature`` is for use in continuous integration with the ``ci_feature`` flow and uses the ``orgs/dev.json`` configuration file.
* ``beta`` is for use in continuous integration or hands-on testing, with the ``ci_beta`` or ``install_beta`` flows. It uses the ``orgs/beta.json`` configuration.
* ``release`` is for use in continuous integration or hands-on testing, with the ``ci_release`` or ``install_prod`` flows. It uses the ``orgs/release.json`` configuration.

Projects may choose to add more orgs by creating further configuration files in the orgs directory and adding entries to their ``orgs:`` section in cumulusci.yml. For example, many projects offer a ``dev_namespaced`` org, a developer org that has a namespace. This org is defined like this: ::

    orgs:
        scratch:
        dev_namespaced:
            config_file: orgs/dev.json
            days: 7
            namespaced: True

This org uses the same SFDX configuration file as the ``dev`` org, but has different configuration in ``cumulusci.yml``, resulting in a different org shape and a different use case.

Your project may have other org shapes defined. ``cci org list`` will show you all of the built-in and custom orgs available for a project.

Tasks and Flows
---------------

CumulusCI uses a framework of *tasks* and *flows* to organize the automation that is available to each project.

Tasks are units of automation. A task could perform a deployment, load a dataset, retrieve material from an org, install a managed package, or undertake many other activities. CumulusCI ships with scores of tasks out of the box. 

You can review the tasks available in a project by running ``cci task list``, learn more about a task and how to configure its options with ``cci task info <name>``, where ``<name>`` is the name of the task, and run a task with ``cci task run <name> --org <org>``, where ``<name>`` is the name of the task and ``<org>`` is the org you’d like to run it against. For example, the ``run_tests`` task executes Apex unit tests. If you have an org called ``dev``, you can run this task against this org with the command ``cci task run run_tests --org dev``.

Many operations that you’ll undertake with CumulusCI, including creating new orgs, use flows. Flows are ordered sequences of tasks (and other flows!) that produce a cohesive outcome, such as an org that’s configured to suit a specific workflow. 

Find the list of flows available in a project by running ``cci flow list``. Learn more about a flow and the tasks it contains with ``cci flow info <name>``, where ``<name>`` is the name of the flow, and run a flow with ``cci flow run <name> --org <org>``, where ``<name>`` is the name of the flow and ``<org>`` is the org you’d like to run it against.

Many of the most common flows you’ll work with in CumulusCI are designed to build and configure specific orgs for you. Here’s a few of the most common flows that build orgs:

* ``dev_org``: This is an unmanaged org that is designed for development use. This flow is typically used with an org whose configuration is ``dev`` or ``dev_namespaced``.
* ``qa_org``: This is an unmanaged org that is designed for testing. This flow is typically used with an org whose configuration is ``qa``.
* ``install_beta``: This is a managed org with the latest beta release installed, for projects that build managed packages. This flow is typically used with an org whose configuration is ``beta``.
* ``install_prod``: This is a managed org with the latest release installed, for projects that build managed packages. 
* ``regression_org``: This is a managed org that starts with the latest release installed and is then upgraded to the latest beta to simulate a subscriber upgrade, for projects that build managed packages. This flow is typically used with an org whose configuration is ``release``.

CumulusCI derives the library of flows and tasks available for any project by combining its internal, out-of-the-box library with the customizations in cumulusci.yml. Customizations can add new tasks and flows, customize the way out-of-the-box tasks behave, and extend, combine, and modify out-of-the-box flows to suit the specific needs of the project.
