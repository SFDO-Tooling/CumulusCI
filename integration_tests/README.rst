This directory contains the Pytest tests which depend on a Salesforce org
or other remote services.

Pytest integration tests are hidden from ordinary ``pytest`` because they are in
a different directory.

You can invoke these tests with the command:

    pytest integration_tests/integration --org <orgname>

--org should be a garbage org that you do not care about because it may be
      changed.

Tests have access to several fixtures:

* runtime - the CumulusCI runtime object
* project_config - project config for the current working directory
* org_config - org config for the selected org
* sf - simple-salesforce client for accessing the selected org's API
* create_task - a factory for creating task instances

