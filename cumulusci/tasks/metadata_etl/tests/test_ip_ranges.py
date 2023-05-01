import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl.permissions import AddIPRanges
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.utils.xml import metadata_tree

PROFILE_BEFORE = b"""<?xml version="1.0" encoding="UTF-8"?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <loginIpRanges>
        <description>Some IP Range</description>
        <startAddress>228.99.236.1</startAddress>
        <endAddress>228.99.236.255</endAddress>
    </loginIpRanges>
</Profile>
"""

MD = "{%s}" % metadata_tree.METADATA_NAMESPACE


@pytest.fixture
def task():
    return create_task(
        AddIPRanges,
        {
            "api_names": ["Admin"],
            "ranges": [
                {
                    "start_address": "127.0.0.1",
                    "end_address": "127.0.0.1",
                },
                {
                    "start_address": "192.168.0.1",
                    "end_address": "192.168.0.254",
                },
                {
                    "description": "foo",
                    "network": "13.108.0.0/14",
                },
            ],
        },
    )


def test_adds_ip_ranges(task):
    tree = metadata_tree.fromstring(PROFILE_BEFORE)
    result = task._transform_entity(tree, "Admin")

    elements = result.findall("loginIpRanges")
    assert len(elements) == 4
    # Existing ranges should be unchanged
    assert elements[0].startAddress.text == "228.99.236.1"
    assert elements[0].endAddress.text == "228.99.236.255"
    # New ranges should be added
    assert elements[1].startAddress.text == "127.0.0.1"
    assert elements[1].endAddress.text == "127.0.0.1"
    assert elements[2].startAddress.text == "192.168.0.1"
    assert elements[2].endAddress.text == "192.168.0.254"
    assert elements[3].startAddress.text == "13.108.0.1"
    assert elements[3].endAddress.text == "13.111.255.254"
    assert elements[3].description.text == "foo"


def test_replaces_ip_ranges(task):
    task.options["replace"] = True
    tree = metadata_tree.fromstring(PROFILE_BEFORE)
    result = task._transform_entity(tree, "Admin")

    elements = result.findall("loginIpRanges")
    assert len(elements) == 3
    # New ranges should be added, with existing ranges removed
    assert elements[0].startAddress.text == "127.0.0.1"
    assert elements[0].endAddress.text == "127.0.0.1"
    assert elements[1].startAddress.text == "192.168.0.1"
    assert elements[1].endAddress.text == "192.168.0.254"
    assert elements[2].startAddress.text == "13.108.0.1"
    assert elements[2].endAddress.text == "13.111.255.254"
    assert elements[2].description.text == "foo"


def test_raises_error_options(task):
    task.options["replace"] = "blah"
    with pytest.raises(TaskOptionsError):
        tree = metadata_tree.fromstring(PROFILE_BEFORE)
        task._transform_entity(tree, "Admin")
