=================
Command Reference
=================

``gist``
===================

The gist command creates a gist comprised of:
    * The current version of ``cci``
    * The current python version
    * The path to the python executable
    * The ``sysname`` of the host (e.g. Darwin)
    * The machine name of the host (e.g. x86_64)
    * The most recent logfile (cci.log) that CumulusCI has created.

The URL for the gist is displayed on the terminal of the user as output, and a web browser will automatically open a tab to the gist.

**Logfiles**

CumulusCI creates a logfile everytime a cci command is run. The only exception to this is when the cci gist command is run. Logfiles are stored either at repository_root/.cci/ or the cwd where a command was run (when run outside the context of a repository configured for use with cci).

**Gist Creation Troubleshooting**

CumulusCI uses the users stored GitHub access token in order to create gists. Access tokens will need to have the ‘create Gist’ scope added to them in order to utilize this command. If CumulusCI detects an error has occurred because of a scoping issue, it will notify the user.


``shell``
===================
The ``shell`` command drops the user into a Python shell with the current CumulusCI configuration loaded.

``version``
==================
The ``version`` command outputs the latest version of CumulusCI along with:
    * The path to the ``cci`` executable
    * The current version of python
    * The path to the python binary in use
