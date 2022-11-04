from contextlib import contextmanager

import pytest

from cumulusci.tasks.bulkdata.delete import DeleteData


@pytest.fixture()
def ensure_accounts(create_task, run_code_without_recording, sf):
    """Delete all accounts and create a certain number of new ones"""

    @contextmanager
    def _ensure_accounts(number_of_accounts):
        def setup(number):
            task = create_task(DeleteData, {"objects": "Entitlement, Account"})
            task()
            for i in range(0, number):
                sf.Account.create({"Name": f"Account {i}"})

        run_code_without_recording(lambda: setup(number_of_accounts))
        yield
        run_code_without_recording(lambda: setup(0))

    return _ensure_accounts
