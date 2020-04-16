from collections import OrderedDict

import json
import yaml
from cumulusci.tasks.salesforce import BaseSalesforceApiTask

yaml.SafeDumper.add_representer(
    OrderedDict,
    lambda dumper, data: dumper.represent_mapping("tag:yaml.org,2002:map", data),
)


class DescribeEverything(BaseSalesforceApiTask):
    def _run_task(self):
        with open("defaults.yml") as default_file:
            data = yaml.safe_load(default_file)
            defaults = data["defaults"]

        rc = {"defaults": defaults, "sobjects": {}}
        global_describe = self.sf.describe()
        for sobject in global_describe["sobjects"]:
            obj = _expand_sobject(self.sf, sobject, defaults)
            name = sobject["name"]
            rc["sobjects"][name] = obj

        with open("out.json", "w") as stream:
            json.dump(rc, stream)


def _expand_sobject(sf_api, sobject, defaults):
    url = sobject["urls"]["describe"]
    full_url = f"https://{sf_api.sf_instance}{url}"
    rc = sf_api.sf._call_salesforce("GET", url=full_url).json()
    rc["fields"] = filter_field_props(rc["fields"], "name", defaults)
    rc["childRelationships"] = filter_field_props(
        rc["childRelationships"], "relationshipName", defaults
    )
    return rc


def filter_field_props(fields, key, defaults):
    return {field[key]: filter_props(field, defaults) for field in fields}


def filter_props(data, defaults):
    return {key: value for (key, value) in data.items() if defaults.get(key) != value}
