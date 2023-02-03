from contextlib import contextmanager
from typing import Dict, List

import pytest

from cumulusci.tasks.bulkdata.delete import DeleteData


@pytest.fixture()
def ensure_records(create_task, run_code_without_recording, sf):
    """Delete all records of an sobject and create a certain number of new ones"""

    @contextmanager
    def _ensure_records(sobjects: Dict[str, List[Dict[str, str]]]):
        def delete():
            task = create_task(DeleteData, {"objects": ",".join(sobjects.keys())})
            task()

        def setup():
            for obj, records in sobjects.items():
                proxy = getattr(sf, obj)
                for record in records:
                    proxy.create(record)

        run_code_without_recording(delete)
        run_code_without_recording(setup)
        yield
        run_code_without_recording(delete)

    return _ensure_records


@pytest.fixture()
def ensure_accounts(ensure_records):
    """Delete all accounts and create a certain number of new ones"""

    @contextmanager
    def _ensure_accounts(number_of_accounts):
        with ensure_records(
            {
                "Entitlement": [],
                "Account": [
                    {"name": f"Account {i}"} for i in range(number_of_accounts)
                ],
            }
        ):
            yield

    return _ensure_accounts
