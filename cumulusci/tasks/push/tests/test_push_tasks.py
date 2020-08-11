import os


from cumulusci.tasks.push.tasks import BaseSalesforcePushTask
from cumulusci.tasks.salesforce.tests.util import create_task

SF_ID = "033xxxxxxxxx"
NAMESPACE = "foo"
NAME = "foo"


def test_load_orgs_file_space():
    # creating sample org file for testing
    # testing with empty file
    with open("output.txt", "w") as file:
        file.write("  \n")
        task = create_task(BaseSalesforcePushTask, options={})
        assert task._load_orgs_file("output.txt") == []
    #
    # testing with multiple orgs
    with open("output.txt", "r") as file:
        assert task._load_orgs_file("output.txt") == []
    os.remove("output.txt")


def test_load_orgs_file():
    # creating sample org file for testing
    # testing with empty file
    with open("output.txt", "w") as file:
        file.write(
            "OrganizationId,OrgName,OrgType,OrgStatus,InstanceName,ErrorSeverity,ErrorTitle,ErrorType,ErrorMessage,Gack Id,Stacktrace Id,\n00D5w000004zLhX,,,,,Error,Unexpected Failure,UnclassifiedError,An unexpected failure was experienced during the upgrade. The subscriber's organization was unaffected. Contact salesforce.com Support through your normal channels and provide the following error number: 1351793968-113330 (-1345328791).,1351793968-113330,-1345328791\n00D5w000005V5Dq,,,,,Error,Unexpected Failure,UnclassifiedError,An unexpected failure was experienced during the upgrade. The subscriber's organization was unaffected. Contact salesforce.com Support through your normal channels and provide the following error number: 822524189-80345 (-2096886284).,822524189-80345,-2096886284"
        )
        task = create_task(BaseSalesforcePushTask, options={})
        assert task._load_orgs_file("output.txt") == []
    #
    # testing with multiple orgs
    with open("output.txt", "r") as file:
        assert task._load_orgs_file("output.txt") == [
            "OrganizationId",
            "00D5w000004zLhX",
            "00D5w000005V5Dq",
        ]
    os.remove("output.txt")
