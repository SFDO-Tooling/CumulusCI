Generate Release Notes
----------------------

The ``github_release_notes`` task fetches the text from Pull Requests that were merged between two given tags. The task then searches for specific titles (Critical Changes, Changes, Issues Closed, New Metadata, Installation Info, and so on) in the Pull Request bodies, and aggregates the text together under those titles in the GitHub tag description.

``github_release_notes`` is automatically run during CumulusCI's built-in release flows.

To see what the release notes look like without publishing them to GitHub:

.. code-block::

    $ cci task run github_release_notes --tag release/1.2

.. note:: The ``--tag`` option indicates which release's change notes are aggregated. The previous command aggregates all change notes between the `1.2` release and the `1.1` release.

To see where each line in the release notes comes from, use the ``--link_pr True`` option.

.. code-block::

    $ cci task run github_release_notes --tag release/1.2 --link_pr True

To publish the release notes to a release tag in GitHub, use the ``--publish True`` option:

.. code-block::

    $ cci task run github_release_notes --tag release/1.2 --publish True

To use additional headings, add new ones (as parsers) under the ``project__git__release_notes`` section of the ``cumulusci.yml`` file.

.. code-block::

    release_notes:
        parsers:
            7: class_path: cumulusci.tasks.release_notes.parser.GithubLinesParser

.. note:: The new parser is listed with the number ``7`` because the first six are the `default parsers <https://github.com/SFDO-Tooling/CumulusCI/blob/671a0e88cef79e9aeefe1e2b835816cd8141bdbb/cumulusci/cumulusci.yml#L1154>`_ that come with CumulusCI.
        