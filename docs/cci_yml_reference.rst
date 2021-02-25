``cumulusci.yml`` Reference
===========================

This section provides a comprehensive list of elements that are valid
to include in a ``cumulusci.yml`` file.

This documentation uses a doubl underscore (``__``) to indicate
levels of indentation within a ``cumulusci.yml`` file. For instance,
given the following yaml:

.. code-block::yaml

    project:
        package:
            name: My CumulusCI Project
            namespace: cci-ns
            api_version: "49.0"

We can refer to the project namespace with ``project__package__namespace``.


project
-------
Most of this is information is created when you setup your project with ``cci project init``.
But other sections like ``dependencies`` may require manual configuration.

dependencies
^^^^^^^^^^^^
A list of 


git
^^^
This section stores information about your project's GitHub repository.
The following elements should be placed under the ``project__git`` section
in a ``cumulusci.yml`` file.

* ``default_branch`` - The default branch for your project (defaults to ``master``).
* ``prefix_beta`` - The prefix your project uses for beta tags (defaults to ``beta/``).
* ``prefix_release`` - The prefix your porject uses for release tags (defaults to ``release/``).
* ``prefix_feature`` - The prefix your porject uses for feature branches (defaults to ``feature/``).
* ``repo_url`` - A URL to the project's GitHub repository.

name
^^^^
Located under ``project__name``. This is the name of your project.

package
^^^^^^^
The following elements should be placed under the ``project__package`` section
in a ``cumulusci.yml`` file.

* ``name`` - The name of your package.
* ``namespace`` - The namespace of your project.
* ``install_class`` - The class to be executed after an installation of your package.
* ``uninstall_class`` - The class to be executed after the package is uninstalled.

source_format
^^^^^^^^^^^^^
This specifies which format your project's metadata adheres to.
Valid values are either ``sfdx`` or <TODO>.


sources
-------


tasks
-----


flows
-----


plans
-----
minimum_cumulusci_version