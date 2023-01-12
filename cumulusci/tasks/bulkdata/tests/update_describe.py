# generate Globals with a certain set of objects.

import json

import yaml

from cumulusci.cli.runtime import CliRuntime

filename = "cumulusci/tests/shared_cassettes/GET_sobjects_Global_describe.yaml"

SELECTED_OBJS = [
    "Account",
    "Contact",
    "Opportunity",
    "Case",
    "Campaign",
    "CampaignMember",
    "Organization",
    "OpportunityContactRole",
]


def init_cci(orgname):
    from cumulusci.salesforce_api.utils import get_simple_salesforce_connection

    runtime = CliRuntime(load_keychain=True)
    name, org_config = runtime.get_org(orgname)
    sf = get_simple_salesforce_connection(runtime.project_config, org_config)
    return sf, runtime, org_config


sf, runtime, org_config = init_cci("qa")
print("Org loaded")

describe_data = sf.describe()
print("Described")
object_list = describe_data["sobjects"]
relevant_objects = [
    obj for obj in object_list if obj["name"] in SELECTED_OBJS
] + object_list[-100:]
describe_data["sobjects"] = relevant_objects

with open(filename) as f:
    yaml_cassette = yaml.safe_load(f)

yaml_cassette["response"]["body"]["string"] = json.dumps(describe_data)

with open(filename, "w") as f:
    yaml.dump(yaml_cassette, f, sort_keys=False, indent=4)
print("Done")
