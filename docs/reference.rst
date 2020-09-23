Reference
=========

Standard Tasks
--------------


Standard Flows
--------------
CumulusCI suite of standard flows can be grouped into various categories depending on their intended purpose.

Continous Integration
^^^^^^^^^^^^^^^^^^^^^^
The suite of continuous integration flows are intended to execute in the context of a CI system.
They typically involve the creation of an org to have tests (Apex and Robot) run against it.
    
``ci_beta``
*****************
This flow installs the latest beta version available and runs apex tests from the managed package. 

.. code-block:: console

    Flow Steps

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


``ci_feature``
*****************
This flow prepares an unmanaged metadata test org and runs Apex tests.
It is intended for use against feature branch commits.

.. code-block:: console

    Flow Steps 

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
        3.1) task: dx_push
            when: project_config.project__source_format == "sfdx" and org_config.scratch
        4) task: uninstall_packaged_incremental
            when: project_config.project__source_format != "sfdx" or not org_config.scratch
    3) flow: config_apextest
        1) task: deploy_post
        2) task: update_admin_profile
    4) task: run_tests
    5) task: github_parent_to_children

``ci_feature_beta_deps``
******************************
This flow installs the latest beta version of dependencies for the project and runs apex tests against them.

.. code-block:: console

    Flow Steps 

    0.5) task: github_parent_pr_notes [from current folder]
    1) flow: beta_dependencies
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
        3.1) task: dx_push
            when: project_config.project__source_format == "sfdx" and org_config.scratch
        4) task: uninstall_packaged_incremental
            when: project_config.project__source_format != "sfdx" or not org_config.scratch
    3) flow: config_apextest
        1) task: deploy_post
        2) task: update_admin_profile
    4) task: run_tests
    5) task: github_parent_to_children

``ci_feature_2gp``
**********************
Install as a managed 2gp package and run Apex tests. Intended for use after build_feature_test_package.

.. code-block:: console

    Flow Steps
    1) task: github_package_data [from current folder]
    2) flow: dependencies
        1) task: update_dependencies
        2) task: deploy_pre
    3) task: install_managed
    4) flow: config_managed
        1) task: deploy_post
        2) task: update_admin_profile
    5) task: run_tests
    6) task: github_parent_to_children


``ci_master``
*****************
Deploy the package metadata to the packaging org and prepare for managed package version upload.  Intended for use against main branch commits.

.. code-block:: console

    Flow Steps 
    1) flow: dependencies [from current folder]
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

``ci_release``
*****************
Install a production release version and runs tests from the managed package

.. code-block:: console

    Flow Steps
    1) flow: install_prod [from current folder]
        1) flow: dependencies
            1) task: update_dependencies
            2) task: deploy_pre
        2) task: install_managed
        3) flow: config_managed
            1) task: deploy_post
            2) task: update_admin_profile
        4) task: snapshot_changes
    2) task: run_tests

Org Configuraiton
^^^^^^^^^^^^^^^^^
Org configuration flows help us automatically configure an org after it has been created.

``config_apextest``
*********************
Configure an org to run apex tests after package metadata is deployed.
.. code-block:: console

    Flow Steps
    1) task: deploy_post
    2) task: update_admin_profile

``config_dev``
********************
Configure an org for use as a dev org after package metadata is deployed.

.. code-block:: console

    Flow Steps
    1) task: deploy_post [from current folder]
    2) task: update_admin_profile

``config_managed``
********************
Configure an org for use as a dev org after package metadata is deployed.

.. code-block:: console

    Flow Steps
    1) task: deploy_post
    2) task: update_admin_profile

``config_packaging``
********************
Configure packaging org for upload after package metadata is deployed.

.. code-block:: console

    Flow Steps
    1) task: update_admin_profile

``config_qa``
********************
Configure an org for use as a QA org after package metadata is deployed.

.. code-block:: console

    Flow Steps
    1) task: deploy_post
    2) task: update_admin_profile

config_regression
********************
Configure an org for QA regression after the package is isntalled.

.. code-block:: console

    Flow Steps
    1) flow: config_managed
        1) task: deploy_post
        2) task: update_admin_profile

Dependency Management
^^^^^^^^^^^^^^^^^^^^^
.. code-block:: console

    Flow Steps

``dependencies``
************************
This flow dpeloys the dependencies specified by your CumulusCI project to prepare an org environment for the package metadata.

.. code-block:: console

    Flow Steps
    1) task: update_dependencies
    2) task: deploy_pre

``beta_dependencies``
************************
This flow deploys the latest beta version of the dependencies to prepare the org environment for the package metadata.

.. code-block:: console

    Flow Steps
    1) task: update_dependencies
    2) task: deploy_pre

Deployment
^^^^^^^^^^

``deploy_unmanaged``
***************************
Deploy the unmanaged metadata from the package.

.. code-block:: console

    Flow Steps
    0) task: dx_convert_from [from current folder]
        when: project_config.project__source_format == "sfdx" and not org_config.scratch
    1) task: unschedule_apex
    2) task: update_package_xml
        when: project_config.project__source_format != "sfdx" or not org_config.scratch
    3) task: deploy
        when: project_config.project__source_format != "sfdx" or not org_config.scratch
    3.1) task: dx_push
        when: project_config.project__source_format == "sfdx" and org_config.scratch
    4) task: uninstall_packaged_incremental
        when: project_config.project__source_format != "sfdx" or not org_config.scratch

``deploy_unmanaged_ee``
***************************

``deploy_packaging``
***************************

Org Creation
^^^^^^^^^^^^
``dev_org``
**************
Set up an org as a development environment for unmanaged metadata

.. code-block:: console

    Flow Steps
    1) flow: dependencies [from current folder]
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
        3.1) task: dx_push
            when: project_config.project__source_format == "sfdx" and org_config.scratch
        4) task: uninstall_packaged_incremental
            when: project_config.project__source_format != "sfdx" or not org_config.scratch
    3) flow: config_dev
        1) task: deploy_post
        2) task: update_admin_profile
    4) task: snapshot_changes

``dev_org_beta_deps``
***************************

``dev_org_namespaced``
***************************

``qa_org``
***************************

``regression_org``
***************************


Install / Uninstall
^^^^^^^^^^^^^^^^^^^
``uninstall_managed``
*****************************

``install_beta``
*****************************

``install_prod``
*****************************

``install_prod_no_config``
*****************************

``install_regression``
*****************************

Release Generation
^^^^^^^^^^^^^^^^^^
``release_beta``
*****************************

``release_production``
*****************************

Utility
^^^^^^^
``build_feature_test_package``
***********************************

``retrieve_scratch``
*****************************

``unamanged_ee``
*****************************

Automated Testing
^^^^^^^^^^^^^^^^^
``robot_docs``
********************************

``test_performance_scratch``
********************************

``test_performance_LDV``
********************************