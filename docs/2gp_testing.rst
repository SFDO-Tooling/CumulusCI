Testing with Second-Generation Packaging
========================================
The Salesforce.org Release Engineering team is harnessing the power of second-generation
managed packages to further enhance the testing of our first-generation managed pacakge products.
Not only does this give us the ability to perform end-to-end testing for packages with more complex
dependency structures sooner in the development lifecycle, but also allows us to build our entire
2GP testing and development framework *before* we migrate our products from 1GP to 2GP. When we
do migrate, we can do so with complete confidence as we will have already been testing our
products as 2GP packages for many months.



2GP Tests for Feature Branches 
------------------------------
The ``ci_feature_2gp`` flow allows us to install a 2GP managed package from a specific commit in GitHub.
This has replaced the need to testing with "namespaced" scratch orgs, as it gives us a more accurate
representation of how namespaces are applied and how metadata will behave once packaged.
Once the 2GP package is installed into the scratch org, all Apex tests are executed.

.. note::

    The ``ci_feature_2gp`` flow is intended for use after the ``build_feature_test_package`` flow.




2GP Testing for Quality Assurance
---------------------------------
The ``qa_org_2gp`` flow allows for performing QA and end-to-end tests of products sooner
in the development lifecycle then was possible before. Take the following example:

* Product B has a dependency on Product A.
* Product B is developing a new feature that are dependent on a new feature that is being developed for Product A.

Prior to testing with 2GP, end-to-end testing on product B could only occur once both products have:

* Merged their feature work into their ``main/`` branch in a source control system.
* New feature metadata has been uploaded to the packaging org
* New Beta version for both Product A and B are created

Once all of the above has occurred, then you can create a scratch org with the new Beta versions
of both packages installed and perform the necessary end-to-end tests. Mind you, if *any* errors are
found at this point the entire process has to start over again. With 2GP testing this is no longer the case.

Let's assume you execute the ``qa_org_2gp`` flow from a feature branch in the repository of Product B.
The following will occur:

#. CumulusCI builds a 2GP package of the contents in product B as they appear in the current branches commit.
#. CumulusCI then looks at the dependencies as they are defined product B's ``cumulusci.yml`` file.
  #. It sees that product A is a dependency.
  #. It goes to product A's GitHub repository and looks for a branch with the same name as the branch in product B.
  #. It builds a 2GP package of product A from this commit
#. CumulusCI then installs the 2GP package for product A, then installs the 2GP package for product B.

This allows for full end-to-end testing of features that have inter-package-dependencies prior to the merging
of code to any long-lived branches (e.g. a release branch or ``main``).