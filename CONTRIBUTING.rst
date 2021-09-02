============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and credit will always be given.
If you are a new contributor, don't forget to add yourself to the `AUTHORS.rst` file in your pull request (either GitHub username, or first/last name). 

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/SFDO-Tooling/CumulusCI/issues.

When reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help wanted" is open to whomever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "enhancement" and "help wanted" is open to whomever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

CumulusCI could always use more documentation, whether as part of the official CumulusCI docs, in docstrings, or even on the web in blog posts, articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an `issue <https://github.com/SFDO-Tooling/CumulusCI/issues>`_.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up CumulusCI for local development.

#. Fork the CumulusCI repo on GitHub.
#. Clone your fork to your local workspace.
#. Create a fresh Python 3 virtual environment and activate it (to keep this isolated from other Python software on your machine). Here is one way::

    $ python3 -m venv cci_venv
    $ source cci_venv/bin/activate

#. Install the development requirements::

    $ make dev-install

#. Install ``pre-commit`` hooks for ``black`` and ``flake8``::

    $ pre-commit install --install-hooks

#. After making changes, run the tests and make sure they all pass::

    $ pytest

#. Your new code should also have meaningful tests. One way to double check that
   your tests cover everything is to ensure that your new code has test code coverage::

   $ make coverage

#. Push your changes to GitHub and submit a Pull Request. The base branch should be a new feature branch that we create to receive the changes (contact us to create the branch). This allows us to test the changes using our build system before merging to main.

.. note:: 

    We enable typeguard with pytest so if you add type declarations to your code, those declarations will be treated as runtime assertions in your Python tests.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

* Documentation is updated to reflect all changes.
* New classes, functions, etc have docstrings.
* New code has comments.
* Code style and file structure is similar to the rest of the project.
* You have run the ``black`` code formatter.

Releasing CumulusCI
-------------------

It's easy to release a version of CumulusCI to GitHub and PyPI! First, create a new branch for your version::

    $ git checkout -b feature/newversion

Make the necessary changes to prepare the new release:

#. Update the version in ``cumulusci/version.txt``
#. Update the release notes in ``HISTORY.rst`` 
    #. Navigate to the latest commits on the ``main`` branch `here <https://github.com/SFDO-Tooling/CumulusCI/commits/main>`_.
    #. Open all merge commits dating back to the previous release.
    #. Content under the "Critical Changes", "Changes", and "Issues Closed" headings of each of the pull request should be aggregated into the same sections under a new entry in the ``HISTORY.rst`` file. 
   


Commit the changes, open a Pull Request on GitHub and request approval from another committer.
Once your PR has been merged, a GitHub action will automatically create the release tag and push the artifacts to PyPI.

After a couple minutes, check for the new release's appearance at `PyPI <https://pypi.org/project/cumulusci/>`_.

Next, head to the tag that was autocreated in the GitHub repository and edit it.
Populate the version number and paste in the changelog notes from ``HISTORY.rst``.
Note that some formatting, such as reStructuredText links, need to be converted to Markdown. Publish the release.

.. note::

    If pandoc is installed on macOS, you can run ``pbpaste | pandoc -f rst -t gfm --wrap none | pbcopy`` to convert from RST to GitHub Flavored Markdown. Chatter handles DOCX input best, so you can run ``pbpaste | pandoc -f gfm -t docx -o /tmp/f.docx && open /tmp/f.docx``

You can then create a pull request to update the `Homebrew Tap`_ by running this locally (note, it's important to do this as soon as possible after the release is published on PyPI, because PyPI is the source CumulusCI checks to see if a new version is available)::

    $ git checkout main
    $ git pull
    $ make release-homebrew

.. note::

    The ``release-homebrew`` build step depends on the `jq`_ command line utility which is available via Homebrew.

That will create a new pull request in the ``SFDO-Tooling/homebrew-sfdo`` repository, which can be merged if its tests pass.

Finally, post the release notes to our usual channels:

- `CumulusCI Release Announcements <https://powerofus.force.com/s/group/0F91E000000DHjTSAW/cumulusci-release-announcements>`_ group in the Power of Us Hub.

    - After posting add topics: CCI Releases & CumulusCI
    
- `CumulusCI group <https://success.salesforce.com/_ui/core/chatter/groups/GroupProfilePage?g=0F9300000009M9ZCAU>`_ in the Trailblazer community. 


.. _Homebrew Tap: https://github.com/SFDO-Tooling/homebrew-sfdo
.. _jq: https://stedolan.github.io/jq/

Org-reliant Automated Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some tests are marked ``@pytest.mark.vcr()`` which means that they can either
call into a real (configured) Salesforce org or use a cached YAML file of the request/response.

By default using pytest will use the cached YAML. If you want to work against a
real scratch org, you do so like this::

    $ pytest --org qa <other arguments and options, such as filename or -k testname>

Where "orgname" is a configured org name like "qa", "dev", etc.

To regenerate the VCR file, you can run this command::

    $ pytest --replace-vcrs --org qa

This will configure an org named "qa" and regenerate them.

That will run all VCR-backed tests against the org, including all of the slow
integration tests.

Running Integration Tests
~~~~~~~~~~~~~~~~~~~~~~~~~

Some tests generate so much data that we do not want to store the VCR cassettes
in our repo. You can mark tests like that with ``@pytest.mark.large_vcr()``. When
they are executed, their cassettes will go in a .gitignore'd folder called
`large_cassettes`.

Do not commit the files ("large_cassettes/\*.yml") to the repository.

Some tests generate even more network traffic data and it isn't practical 
to use VCR at all. Still, we'd like to run them when we run all of the
other org-reliant tests with --org. Mark them with ``@pytest.mark.needs_org()``
and they will run with the VCR tests.

Some tests are so slow that you only want to run them on an opt-in basis.
Mark these tests with ``@pytest.mark.slow()`` and run them with
``pytest --run-slow-tests`` or ``pytest --run-slow-tests --orgname <orgname>``.

Writing Integration Tests
~~~~~~~~~~~~~~~~~~~~~~~~~
All features should have integration tests which work against
real orgs or APIs.

You will need to use some the following fixtures in your tests. Search
the repo to see examples where they are used in context, or to see
their definitions:

* gh_api - get a fake github API
* with temp_db():... - create a temporary SQLite Database
* delete_data_from_org("Account,Contacts") - delete named sobjects from an org
* run_code_without_recording(func) - run a function ONLY when
  the integration tests are being used against real orgs
  and DO NOT record the network traffic in a VCR cassette
* sf - a handle to a simple-salesforce client tied to the
  current org
* mock_http_response(status) - make a mock HTTP Response with a particular status
* runtime - Get the CumulusCI runtime for the current working directory
* project_config - Get the project config for the current working directory
* org_config - Get the project config for the current working directory
* create_task - Get a task _factory_ which can be used to construct task instances.

Decorators for tests:

 * pytest.mark.slow(): a slow test that should only be executed when requested with --run-slow-tests
 * pytest.mark.large_vcr(): a network-based test that generates VCR cassettes too large for version control. Use --org to generate them locally.
 * pytest.mark.needs_org(): a test that needs an org (or at least access to the network) but should not attempt to store VCR cassettes. Most tests that need network access do so because they need to talk to an org, but you can also use this decorator to give access to the network to talk to github or any other API.
 * org_shape('qa', 'qa_org'): - switch the current org to an org created with org template "qa" after running flow "qa_org".
   As with all tests, clean up any changes you make, because this org may be reused by
   other tests.

Randomized tests
~~~~~~~~~~~~~~~~

Tests should be executable in any order. You can run this command
a few times to verify if they are:

    pytest --random-order

It will output something like this:

    Using --random-order-bucket=module
    Using --random-order-seed=986925

Using those two parameters on the command line, you can
replicate a particular run later.

In extremely rare cases where it's not possible to make
tests independent, you can
`enforce an order <https://pythonhosted.org/pytest-random-order/#disable-shuffling-in-module-or-class>`_
