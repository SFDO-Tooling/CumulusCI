==============
Why CumulusCI?
==============

CumulusCI was built to solve common challenges faced the development and release of Salesforce managed package projects such as:

* Integration of Salesforce DX into the package release cycle
* Reducing the burden and risk of cutting managed package releases
* Agile development based on best practices of isolation and continuous integration
* Reducing the pain of creating usable environments for QA, Doc, PM, etc
* Scalability to handle new projects and growing project teams
* Avoiding technical debt by encouraging reuse through portable automation

CumulusCI is a framework for building portable automation for Salesforce projects on Github.  The automation is controlled by a simple **cumulusci.yml** file which is version controlled in the project repository and is available to anyone with CumulusCI configured on their system and able to access the repository.

We've used CumulusCI every day at Salesforce.org to run over 17k+ builds of 12 Github managed package repositories for our products.  The goal of making CumulusCI available as open source is to empower other Salesforce developers to benefit from the solutions to common challenges faced in managing the development and release cycle of Saleforce managed packages.

Portable Automation
===================

Portable Automation is a core philosophy of CumulusCI bred from our 4+ years experience building a scalable development and release process for our managed package projects at Salesforce.org.  We started like most people did at the time, writing Ant targets and getting them to run through Jenkins.  After about a year, we came to realize that writing scripts with Jenkins as the primary user persona was missing a lot of potential to reuse the automation we invested in creating for our builds.

If you're creating automation that helps you do something useful with a Salesforce org to prepare a development or test environment, there are likely many people involved in your project who could also benefit from that automation:

* **Release Engineers** who need to debug build failures by running the scripts locally
* **Developers** who need to create new development environments for different feature branches
* **QAs** who need to create test environments from feature branches and managed package installs
* **Doc Writers** who need to create environments to interact with new features and capture screenshots to prepare documentation for a release
* **Product Managers** who need to create test environments with new features and releases to provide feedback on feature implementations
* **Partners** who need to create test and development environments to build on top of your package
* **Web Apps** you can build to reuse the automation logic (i.e. custom CI app, web based installers, etc)

CumulusCI aims to expand the scope of automation to handle all these use cases through Portable Automation.

User Experience
===============

We work with CumulusCI every day.  When we started work on the rewrite of CumulusCI in 2015, we set out to build a tool that we loved to use every day.  That meant a real investment in a core framework to enable the best user experience we could imagine.  This section highlights some of the key user experience features of CumulusCI.

Common Names Across Repositories
--------------------------------

By providing a set of common tasks and flows to all projects, CumulusCI makes it easier to work across multiple project repositories.  For example, every CumulusCI project has a flow named **dev_org** which is used to deploy a development instance of unmanaged code from the repository (typically a feature branch).  Since projects are able to modify the **dev_org** flow, developers never have to remember flow names like **dev_org_projectA** and **dev_org_projectB**.

Similarly, CumulusCI provides 4 scratch org definitions by default to all projects which are useful for different phases of a typical project's development lifecycle:

* **beta**: A DE org intended for testin beta releases
* **dev**: A DE org intended for unmanaged deploys of development environments
* **feature**: A DE org intended for testing of unmanaged deploys
* **release**: An EE org intended for testing production releases

Developers always have these 4 org types available to create and use in any CumulusCI project while each project can customize the configuration for each org to the needs of the project.

Local Repository Aware
----------------------

CumulusCI knows what local repository you are inside of and tries to create the best user experience possible.  For example, we automatically namespace your orgs by your project name for you so rather than typing **ProjectRepoA_dev** to access the dev org for **ProjectRepoA**, you just change directories into your local clone of **ProjectRepoA** and access an org named **dev**.

CumulusCI's core project_config object provides access to a lot of information about your project including the local repo root, current commit, current branch, and an authenticated instance of the **github3.py** wrapper for the Github API, all of which are available for use in custom task classes.

Override Based Configuration
----------------------------

CumulusCI aims to reduce the amount of skeleton code required to configure a project.  This is accomplished by a merged yaml file, **cumulusci.yml** which starts from the global yaml from CumulusCI with all the standard project, task, flow, and org configurations.  Projects can then override the default values in their **cumulusci.yml**.  This means that by looking at the **cumulusci.yml** of a repository using CumulusCI, you can easily see all customization of CumulusCI done for the project.

The following example is of a simple **cumulusci.yml** file with only a few overrides:
https://github.com/SalesforceFoundation/CumulusCI-Test/blob/master/cumulusci.yml

The following example is from the Nonprofit Success Pack and shows a heavily configured **cumulusci.yml** file: 
https://github.com/SalesforceFoundation/Cumulus/blob/master/cumulusci.yml

Both of these projects have all the standard CumulusCI tasks, flows, and orgs available to them in addition to project specific custom tasks, flows, and orgs defined in the **cumulusci.yml** for the project.

Yaml Over Python, Where Possible
--------------------------------

Although CumulusCI is written in Python, the framework for CumulusCI was designed to allow the majority of automation use cases to be handled solely in the **cumulusci.yml** file.  All tasks are implemented in Python classes, but each task can define its own task specific options.  We've tried to design all the included tasks with a number of options to allow easy reuse through yaml configuration.

For example, if you want to deploy a custom directory of metadata named **dev_config** after your **src** directory's metadata is deployed, you could create the task and wire it into the default **dev_org** flow with the following yaml

.. code-block:: yaml 

    tasks:
        deploy_dev_config:
            description: Deploys the dev_config directory to configure a development instance
            class_path: cumulusci.tasks.salesforce.Deploy
            options:
                path: dev_config 
    flows:
        dev_org:
            8:  # Add a new slot at the end of the flow
                task: deploy_dev_config

With no Python code, we've just added the deployment of an additional directory of metadata to all future dev environment setups.

While the goal is to make as much available via yaml, it's still possible and quite simple to write your own custom tasks for CumulusCI in Python.  You can even reuse and subclass our task classes to make the process easier.

Friendly Logging Output
-----------------------

We invested a lot in making the logging output from running CumulusCI tasks as useful as possible.  For example, we progressively increase the polling interval every 3 polling attempts on polling processes which are known to take a while such as the **Pending** stage of a Metadata API deployment.  For a deploy which is pending for 5 minutes, this could mean the difference of 600 lines of output (1 poll/sec) vs 60 lines of output.  When run through a CI system, this makes our build logs much shorter and easier to read.

As a bonus, features like progressively increasing polling intervals also help reduce the risk of hitting an API Limit in your Salesforce Org!

Does CumulusCI Compete With Salesforce DX?
==========================================

In short... NO :)

CumulusCI works with Salesforce DX to provide a prescriptive orchestration layer for easily running the CumulusCI Flow process for Salesforce development projects hosted in Github.  In most of the Salesforce DX documentation, orchestration is handled by bash shell scripts.  In that sense, CumulusCI is more a competitor to bash than to Salesforce DX.

There are some key differentiators to how CumulusCI works in comparison to Salesforce DX which are worth noting:

* CumulusCI is prescriptive out of the box while Salesforce DX intends to be a lower level toolbelt which is process and tooling agnostic.  For example, CumulusCI assumes your project is hosted in Github.  While it is possible to use CumulusCI without Github, we operate from the assumption that the vast majority of users will use Github and try to make that use case as easy as possible.
* CumulusCI is more focused on defining portable automation and orchestration for projects
* CumulusCI provides a complete development process out of the box which can be easily customized by each project
* CumulusCI is open source, licensed under a BSD 3-Clause License
* CumulusCI's ability to encapsulate more complex commands into a single named task via the **cumulusci.yml** creates a cleaner CLI user experience that reduces risk of human error from forgetting an option flag

We've been running CumulusCI with Salesforce DX for over a year in over 17k+ production builds at Salesforce.org.  The combination provides us the best of both worlds while allowing us to incrementally migrate pieces of our orchestration to Salesforce DX where it makes sense.

Only in CumulusCI
=================

CumulusCI has a number of unique capabilities that you won't find in any other tooling to work with Salesforce projects:

* **Automated Release Notes**: CumulusCI's **release_beta** flow uses the **github_release_notes** task to automatically parse the bodies of pull requests merged since the last production release and generate combined release notes from the content.
* **Bulk API Query/Load**: CumulusCI includes Python task classes allowing for the creation of multi-object relational data set mappings used to query data from a Salesforce org into a local sqlite database and insert that relational data into another Salesforce org.
* **Dependency Management**: CumulusCI includes robust support for project dependencies including managed packages, unmanaged metadata, and references to other CumulusCI project repositories to dynamically and recursively inherit the referenced project's dependencies
* **Apex Limit Reports for Tests**: CumulusCI's Apex test runner outputs a **test_results.json** file which includes the duration and Apex limits usage for each test method executed
* **Update Admin Profile**: All CumulusCI flows run the **update_admin_profile** task to retrieve the Admin.profile from the target org after deploying the package or the package source, grant FLS permissions on all fields and classes, and deploy the updated profile.  This makes it easier to get up an running with a useable environment from a fresh scratch org.
* **Push API**: Automate push upgrades of your product using the Push API and CumulusCI's built in tasks: **push_all**, **push_sandbox**, **push_trial**, and **push_qa**
* **meta.xml File Management**: Unmanaged deploys automatically strip namespace, majorVersion, and minorVersion elements from the meta.xml file allowing CumulusCI's dependency management to handle your dependencies.  Also, the **meta_xml_dependencies** and **meta_xml_apiversion** tasks automate updating all local meta.xml files with the api_version specified in **cumulusci.yml** and the namespace, majorVersion, and minorVersion of the currently resolved dependencies.
* **MetaCI**: MetaCI is our custom CI app run on Heroku to automate the execution of builds using CumulusCI flows.  It is Salesforce aware and can handle burst capacity for builds by leveraging Heroku's scalability.

Next Steps
==========

Interested in trying it out?  Check out the CumulusCI :doc:`tutorial`

Want to find out more about our development and release process?  Check out :doc:`cumulusci_flow`
