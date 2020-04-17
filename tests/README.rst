This directory contains the Pytest tests which depend on a Salesforce org
or other remote services.

Pytest integration tests are hidden from ordinary `pytest` because they are in
a different directory.

You can invoke these test with the CCI task:

pytest tests/integration --org <orgname>

You can leave out the --org option if you have an org defaulted.

Tests have access to two fixtures:
* create_task(task_class:class, task_options:dict)
* sf - a Salesforce instance