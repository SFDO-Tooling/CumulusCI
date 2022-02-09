import responses

from cumulusci.tasks.marketing_cloud.mc_constants import MC_API_VERSION
from cumulusci.tasks.marketing_cloud.util import get_mc_stack_key

STACK_KEY = "S4"
TSSD = "asdf-qwerty"


@responses.activate
def test_marketing_cloud_get_stack_key():
    responses.add(
        "GET",
        f"https://{TSSD}.auth.marketingcloudapis.com/{MC_API_VERSION}/userinfo",
        json={"organization": {"stack_key": STACK_KEY}},
    )
    assert STACK_KEY == get_mc_stack_key(TSSD, "fake-access-token")
