Flow Reference
==========================================

CumulusCI's suite of standard flows are grouped into various categories depending on their intended purpose.

.. contents::
    :depth: 2
    :local:


Org Setup
---------
These are the primary flows for doing full setup of an org.
They typically include a flow from the Dependency Management group,
a flow from either the Deployment or Install / Uninstall group,
and a flow from the Post-Install Configuration group.

dev_org
^^^^^^^

**Description:** Set up an org as a development environment for unmanaged metadata

**Flow Steps**

.. code-block:: console

	1) flow: dependencies
	    1) task: update_dependencies
	    2) task: deploy_pre
	2) flow: deploy_unmanaged
	    0) task: dx_convert_from
	       when: project_config.project__source_format == "sfdx" and not org_config.scratch
	    1) task: unschedule_apex
	    2) task: update_package_xml
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    3) task: deploy
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    3.1) task: deploy
	         when: project_config.project__source_format == "sfdx" and org_config.scratch
	    4) task: uninstall_packaged_incremental
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    5) task: snapshot_changes
	3) flow: config_dev
	    1) task: deploy_post
	    2) task: update_admin_profile
	4) task: snapshot_changes

dev_org_beta_deps
^^^^^^^^^^^^^^^^^

**Description:** This flow is deprecated. Please use dev_org instead.

**Flow Steps**

.. code-block:: console

	1) flow: dependencies
	    1) task: update_dependencies
	    2) task: deploy_pre
	2) flow: deploy_unmanaged
	    0) task: dx_convert_from
	       when: project_config.project__source_format == "sfdx" and not org_config.scratch
	    1) task: unschedule_apex
	    2) task: update_package_xml
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    3) task: deploy
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    3.1) task: deploy
	         when: project_config.project__source_format == "sfdx" and org_config.scratch
	    4) task: uninstall_packaged_incremental
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    5) task: snapshot_changes
	3) flow: config_dev
	    1) task: deploy_post
	    2) task: update_admin_profile

dev_org_namespaced
^^^^^^^^^^^^^^^^^^

**Description:** Set up a namespaced scratch org as a development environment for unmanaged metadata

**Flow Steps**

.. code-block:: console

	1) flow: dependencies
	    1) task: update_dependencies
	    2) task: deploy_pre
	2) flow: deploy_unmanaged
	    0) task: dx_convert_from
	       when: project_config.project__source_format == "sfdx" and not org_config.scratch
	    1) task: unschedule_apex
	    2) task: update_package_xml
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    3) task: deploy
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    3.1) task: deploy
	         when: project_config.project__source_format == "sfdx" and org_config.scratch
	    4) task: uninstall_packaged_incremental
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    5) task: snapshot_changes
	3) flow: config_dev
	    1) task: deploy_post
	    2) task: update_admin_profile
	4) task: snapshot_changes

install_beta
^^^^^^^^^^^^

**Description:** Install and configure the latest beta version

**Flow Steps**

.. code-block:: console

	1) flow: dependencies
	    1) task: update_dependencies
	    2) task: deploy_pre
	2) task: install_managed_beta
	3) flow: config_managed
	    1) task: deploy_post
	    2) task: update_admin_profile
	4) task: snapshot_changes

install_prod
^^^^^^^^^^^^

**Description:** Install and configure the latest production version

**Flow Steps**

.. code-block:: console

	1) flow: dependencies
	    1) task: update_dependencies
	    2) task: deploy_pre
	2) task: install_managed
	3) flow: config_managed
	    1) task: deploy_post
	    2) task: update_admin_profile
	4) task: snapshot_changes

qa_org
^^^^^^

**Description:** Set up an org as a QA environment for unmanaged metadata

**Flow Steps**

.. code-block:: console

	1) flow: dependencies
	    1) task: update_dependencies
	    2) task: deploy_pre
	2) flow: deploy_unmanaged
	    0) task: dx_convert_from
	       when: project_config.project__source_format == "sfdx" and not org_config.scratch
	    1) task: unschedule_apex
	    2) task: update_package_xml
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    3) task: deploy
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    3.1) task: deploy
	         when: project_config.project__source_format == "sfdx" and org_config.scratch
	    4) task: uninstall_packaged_incremental
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    5) task: snapshot_changes
	3) flow: config_qa
	    1) task: deploy_post
	    2) task: update_admin_profile
	4) task: snapshot_changes

regression_org
^^^^^^^^^^^^^^

**Description:** Simulates an org that has been upgraded from the latest release of to the current beta and its dependencies, but deploys any unmanaged metadata from the current beta.

**Flow Steps**

.. code-block:: console

	1) flow: install_regression
	    1) flow: dependencies
	        1) task: update_dependencies
	        2) task: deploy_pre
	    2) task: install_managed
	    3) task: install_managed_beta
	2) flow: config_regression
	    1) flow: config_managed
	        1) task: deploy_post
	        2) task: update_admin_profile
	3) task: snapshot_changes

Dependency Management
---------------------
These flows deploy dependencies (base packages and unmanaged metadata) to a target org environment.

beta_dependencies
^^^^^^^^^^^^^^^^^

**Description:** This flow is deprecated. Please use the `dependencies` flow and set the `include_beta` option on the first task, `update_dependencies`. Deploy the latest (beta) version of dependencies to prepare the org environment for the package metadata

**Flow Steps**

.. code-block:: console

	1) task: update_dependencies
	2) task: deploy_pre

dependencies
^^^^^^^^^^^^

**Description:** Deploy dependencies to prepare the org environment for the package metadata

**Flow Steps**

.. code-block:: console

	1) task: update_dependencies
	2) task: deploy_pre

Deployment
----------
These flows deploy the main package metadata to a target org environment.

deploy_packaging
^^^^^^^^^^^^^^^^

**Description:** Process and deploy the package metadata to the packaging org

**Flow Steps**

.. code-block:: console

	0) task: dx_convert_from
	   when: project_config.project__source_format == "sfdx"
	1) task: unschedule_apex
	2) task: create_managed_src
	3) task: update_package_xml
	4) task: deploy
	5) task: revert_managed_src
	6) task: uninstall_packaged_incremental

deploy_unmanaged
^^^^^^^^^^^^^^^^

**Description:** Deploy the unmanaged metadata from the package

**Flow Steps**

.. code-block:: console

	0) task: dx_convert_from
	   when: project_config.project__source_format == "sfdx" and not org_config.scratch
	1) task: unschedule_apex
	2) task: update_package_xml
	   when: project_config.project__source_format != "sfdx" or not org_config.scratch
	3) task: deploy
	   when: project_config.project__source_format != "sfdx" or not org_config.scratch
	3.1) task: deploy
	     when: project_config.project__source_format == "sfdx" and org_config.scratch
	4) task: uninstall_packaged_incremental
	   when: project_config.project__source_format != "sfdx" or not org_config.scratch
	5) task: snapshot_changes

deploy_unmanaged_ee
^^^^^^^^^^^^^^^^^^^

**Description:** Deploy the unmanaged metadata from the package to an Enterprise Edition org

**Flow Steps**

.. code-block:: console

	0) task: dx_convert_from
	   when: project_config.project__source_format == "sfdx"
	1) task: unschedule_apex
	2) task: update_package_xml
	3) task: create_unmanaged_ee_src
	4) task: deploy
	5) task: revert_unmanaged_ee_src
	6) task: uninstall_packaged_incremental

unmanaged_ee
^^^^^^^^^^^^

**Description:** Deploy the unmanaged package metadata and all dependencies to the target EE org

**Flow Steps**

.. code-block:: console

	1) flow: dependencies
	    1) task: update_dependencies
	    2) task: deploy_pre
	2) flow: deploy_unmanaged_ee
	    0) task: dx_convert_from
	       when: project_config.project__source_format == "sfdx"
	    1) task: unschedule_apex
	    2) task: update_package_xml
	    3) task: create_unmanaged_ee_src
	    4) task: deploy
	    5) task: revert_unmanaged_ee_src
	    6) task: uninstall_packaged_incremental

Install / Uninstall
-------------------
These flows handle package installation and uninstallation in particular scenarios.

install_prod_no_config
^^^^^^^^^^^^^^^^^^^^^^

**Description:** Install but do not configure the latest production version

**Flow Steps**

.. code-block:: console

	1) flow: dependencies
	    1) task: update_dependencies
	    2) task: deploy_pre
	2) task: install_managed
	3) task: deploy_post

install_regression
^^^^^^^^^^^^^^^^^^

**Description:** Install the latest beta dependencies and upgrade to the latest beta version from the most recent production version

**Flow Steps**

.. code-block:: console

	1) flow: dependencies
	    1) task: update_dependencies
	    2) task: deploy_pre
	2) task: install_managed
	3) task: install_managed_beta

uninstall_managed
^^^^^^^^^^^^^^^^^

**Description:** Uninstall the installed managed version of the package.  Run this before install_beta or install_prod if a version is already installed in the target org.

**Flow Steps**

.. code-block:: console

	1) task: uninstall_post
	2) task: uninstall_managed

Post-Install Configuration
--------------------------
These flows perform configuration after the main package has been installed or deployed.

config_apextest
^^^^^^^^^^^^^^^

**Description:** Configure an org to run apex tests after package metadata is deployed

**Flow Steps**

.. code-block:: console

	1) task: deploy_post
	2) task: update_admin_profile

config_dev
^^^^^^^^^^

**Description:** Configure an org for use as a dev org after package metadata is deployed

**Flow Steps**

.. code-block:: console

	1) task: deploy_post
	2) task: update_admin_profile

config_managed
^^^^^^^^^^^^^^

**Description:** Configure an org for use after the managed package has been installed.

**Flow Steps**

.. code-block:: console

	1) task: deploy_post
	2) task: update_admin_profile

config_packaging
^^^^^^^^^^^^^^^^

**Description:** Configure packaging org for upload after package metadata is deployed

**Flow Steps**

.. code-block:: console

	1) task: update_admin_profile

config_qa
^^^^^^^^^

**Description:** Configure an org for use as a QA org after package metadata is deployed

**Flow Steps**

.. code-block:: console

	1) task: deploy_post
	2) task: update_admin_profile

config_regression
^^^^^^^^^^^^^^^^^

**Description:** Configure an org for QA regression after the package is installed

**Flow Steps**

.. code-block:: console

	1) flow: config_managed
	    1) task: deploy_post
	    2) task: update_admin_profile

Continuous Integration
----------------------
These flows are designed to be run automatically by a continuous integration (CI) system
in response to new commits. They typically set up an org and run Apex tests.

ci_beta
^^^^^^^

**Description:** Install the latest beta version and runs apex tests from the managed package

**Flow Steps**

.. code-block:: console

	1) flow: install_beta
	    1) flow: dependencies
	        1) task: update_dependencies
	        2) task: deploy_pre
	    2) task: install_managed_beta
	    3) flow: config_managed
	        1) task: deploy_post
	        2) task: update_admin_profile
	    4) task: snapshot_changes
	2) task: run_tests

ci_feature
^^^^^^^^^^

**Description:** Prepare an unmanaged metadata test org and run Apex tests. Intended for use against feature branch commits.

**Flow Steps**

.. code-block:: console

	0.5) task: github_parent_pr_notes
	1) flow: dependencies
	    1) task: update_dependencies
	    2) task: deploy_pre
	2) flow: deploy_unmanaged
	    0) task: dx_convert_from
	       when: project_config.project__source_format == "sfdx" and not org_config.scratch
	    1) task: unschedule_apex
	    2) task: update_package_xml
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    3) task: deploy
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    3.1) task: deploy
	         when: project_config.project__source_format == "sfdx" and org_config.scratch
	    4) task: uninstall_packaged_incremental
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    5) task: snapshot_changes
	3) flow: config_apextest
	    1) task: deploy_post
	    2) task: update_admin_profile
	4) task: run_tests
	5) task: github_automerge_feature

ci_feature_2gp
^^^^^^^^^^^^^^

**Description:** Install as a managed 2gp package and run Apex tests. Intended for use after build_feature_test_package.

**Flow Steps**

.. code-block:: console

	1) task: github_package_data
	2) flow: dependencies
	    1) task: update_dependencies
	    2) task: deploy_pre
	3) task: install_managed
	4) flow: config_managed
	    1) task: deploy_post
	    2) task: update_admin_profile
	5) task: run_tests

ci_feature_beta_deps
^^^^^^^^^^^^^^^^^^^^

**Description:** This flow is deprecated. Please use ci_feature instead.

**Flow Steps**

.. code-block:: console

	0.5) task: github_parent_pr_notes
	1) flow: dependencies
	    1) task: update_dependencies
	    2) task: deploy_pre
	2) flow: deploy_unmanaged
	    0) task: dx_convert_from
	       when: project_config.project__source_format == "sfdx" and not org_config.scratch
	    1) task: unschedule_apex
	    2) task: update_package_xml
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    3) task: deploy
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    3.1) task: deploy
	         when: project_config.project__source_format == "sfdx" and org_config.scratch
	    4) task: uninstall_packaged_incremental
	       when: project_config.project__source_format != "sfdx" or not org_config.scratch
	    5) task: snapshot_changes
	3) flow: config_apextest
	    1) task: deploy_post
	    2) task: update_admin_profile
	4) task: run_tests
	5) task: github_automerge_feature

ci_master
^^^^^^^^^

**Description:** Deploy the package metadata to the packaging org and prepare for managed package version upload.  Intended for use against main branch commits.

**Flow Steps**

.. code-block:: console

	1) flow: dependencies
	    1) task: update_dependencies
	    2) task: deploy_pre
	2) flow: deploy_packaging
	    0) task: dx_convert_from
	       when: project_config.project__source_format == "sfdx"
	    1) task: unschedule_apex
	    2) task: create_managed_src
	    3) task: update_package_xml
	    4) task: deploy
	    5) task: revert_managed_src
	    6) task: uninstall_packaged_incremental
	3) flow: config_packaging
	    1) task: update_admin_profile

ci_release
^^^^^^^^^^

**Description:** Install a production release version and runs tests from the managed package

**Flow Steps**

.. code-block:: console

	1) flow: install_prod
	    1) flow: dependencies
	        1) task: update_dependencies
	        2) task: deploy_pre
	    2) task: install_managed
	    3) flow: config_managed
	        1) task: deploy_post
	        2) task: update_admin_profile
	    4) task: snapshot_changes
	2) task: run_tests

Release Operations
------------------
These flows are used to release new package versions.

build_feature_test_package
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Description:** Create a 2gp managed package version

**Flow Steps**

.. code-block:: console

	1) task: update_package_xml
	   when: project_config.project__source_format != "sfdx"
	2) task: create_package_version

release_beta
^^^^^^^^^^^^

**Description:** Upload and release a beta version of the metadata currently in packaging

**Flow Steps**

.. code-block:: console

	1) task: upload_beta
	2) task: github_release
	3) task: github_release_notes
	4) task: github_automerge_main

release_production
^^^^^^^^^^^^^^^^^^

**Description:** Upload and release a production version of the metadata currently in packaging

**Flow Steps**

.. code-block:: console

	1) task: upload_production
	2) task: github_release
	3) task: github_release_notes

Other
-----
This is a catch-all group for any flows without a designated "group" attribute in ``cumulusci.yml``.

robot_docs
^^^^^^^^^^

**Description:** Generates documentation for robot framework libraries

**Flow Steps**

.. code-block:: console

	1) task: robot_libdoc
	2) task: robot_testdoc

test_performance_LDV
^^^^^^^^^^^^^^^^^^^^

**Description:** Test performance in an LDV org

**Flow Steps**

.. code-block:: console

	1) task: robot

test_performance_scratch
^^^^^^^^^^^^^^^^^^^^^^^^

**Description:** Test performance of a scratch org

**Flow Steps**

.. code-block:: console

	1) task: robot

