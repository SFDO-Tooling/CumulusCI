import datetime
import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.push.tasks import SchedulePushOrgList
from cumulusci.tasks.salesforce.tests.util import create_task

SF_ID = "033xxxxxxxxx"
NAMESPACE = "foo"
NAME = "foo"
ORG_FILE = "output.csv"
VERSION = "1.2.3"
ORG = "00DS0000003TJJ6MAO"
ORG_FILE_TEXT = """\n00DS0000003TJJ6MAO\n00DS0000003TJJ6MAL"""
REAL_ORG_FILE_TEXT = """OrganizationId,OrgName,OrgType,OrgStatus,InstanceName,ErrorSeverity,ErrorTitle,ErrorType,ErrorMessage,Gack Id,Stacktrace Id,\n00D5w000004zXXX,,,,,Error,Unexpected Failure,UnclassifiedError,An unexpected failure was experienced during the upgrade. The subscriber's organization was unaffected. Contact salesforce.com Support through your normal channels and provide the following error number: 1351793968-113330 (-1345328791).,1351793968-113330,-1345328791\n00D5w000005VXXX,,,,,Error,Unexpected Failure,UnclassifiedError,An unexpected failure was experienced during the upgrade. The subscriber's organization was unaffected. Contact salesforce.com Support through your normal channels and provide the following error number: 822524189-80345 (-2096886284).,822524189-80345,-2096886284"""


def test_schedule_push_org_list_get_orgs_formatted(tmp_path):
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    orgs = tmp / ORG_FILE
    orgs.write_text(ORG_FILE_TEXT)
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": orgs,
            "version": VERSION,
            "namespace": NAMESPACE,
            "start_time": datetime.datetime.now(),
            "batch_size": 10,
        },
    )
    assert task._get_orgs() == ["00DS0000003TJJ6MAO", "00DS0000003TJJ6MAL"]


def test_schedule_push_org_list_get_orgs(tmp_path):
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    orgs = tmp / ORG_FILE
    orgs.write_text(REAL_ORG_FILE_TEXT)
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": orgs,
            "version": VERSION,
            "namespace": NAMESPACE,
            "start_time": datetime.datetime.now(),
            "batch_size": 10,
            "csv_field_name": "OrganizationId",
            "csv": ORG_FILE,
        },
    )
    assert task._get_orgs() == ["00D5w000004zXXX", "00D5w000005VXXX"]


def test_schedule_push_org_list_get_error(tmp_path):
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    orgs = tmp / ORG_FILE
    orgs.write_text(REAL_ORG_FILE_TEXT)
    with pytest.raises(TaskOptionsError):
        task = create_task(
            SchedulePushOrgList,
            options={
                "orgs": orgs,
                "version": VERSION,
                "namespace": NAMESPACE,
                "start_time": datetime.datetime.now(),
                "batch_size": 10,
                "csv_field_name": "OrganizationId",
            },
        )
        assert task._get_orgs() == ["00D5w000004zXXX", "00D5w000005V5XXX"]


# Should set csv_field_name to OrganizationId by default
def test_schedule_push_org_list_get_default(tmp_path):
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    orgs = tmp / ORG_FILE
    orgs.write_text(ORG_FILE_TEXT)
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": orgs,
            "version": VERSION,
            "namespace": NAMESPACE,
            "start_time": datetime.datetime.now(),
            "batch_size": 10,
        },
    )
    assert task._get_orgs() == ["00DS0000003TJJ6MAO", "00DS0000003TJJ6MAL"]
    assert task.options["csv_field_name"] == "OrganizationId"


def test_schedule_push_org_list_no_file(tmp_path):
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    orgs = tmp / ORG_FILE
    orgs.write_text(ORG_FILE_TEXT)
    with pytest.raises(TaskOptionsError):
        task = create_task(
            SchedulePushOrgList,
            options={
                "version": VERSION,
                "namespace": NAMESPACE,
                "start_time": datetime.datetime.now(),
                "batch_size": 10,
            },
        )
        assert task._get_orgs() == ["00DS0000003TJJ6MAO", "00DS0000003TJJ6MAL"]
