from unittest.mock import Mock

from cumulusci.tasks.salesforce.salesforce_files import ListFiles
from cumulusci.tasks.salesforce.tests.util import create_task


class TestDisplayFiles:
    def test_display_files(self):
        task = create_task(ListFiles, {})
        task._init_api = Mock()
        task._init_api.return_value.query.return_value = {
            "totalSize": 2,
            "records": [
                {"Title": "TEST1", "Id": "0PS000000000000", "FileType": "TXT"},
                {"Title": "TEST2", "Id": "0PS000000000001", "FileType": "TXT"},
            ],
        }
        task()

        task._init_api.return_value.query.assert_called_once_with(
            "SELECT Title, Id, FileType FROM ContentDocument"
        )
        assert task.return_values == [
            {"Id": "0PS000000000000", "FileName": "TEST1", "FileType": "TXT"},
            {"Id": "0PS000000000001", "FileName": "TEST2", "FileType": "TXT"},
        ]
