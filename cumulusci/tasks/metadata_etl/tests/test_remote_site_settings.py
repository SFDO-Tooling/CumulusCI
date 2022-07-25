from pathlib import Path
from tempfile import TemporaryDirectory
from xml.dom.minidom import parseString

from cumulusci.tasks.metadata_etl.remote_site_settings import (
    RSS_DIR_NAME,
    RSS_FILE_EXTENSION,
    AddRemoteSiteSettings,
)
from cumulusci.tasks.salesforce.tests.util import create_task


class TestAddRemoteSiteSettings:
    def test_synthesis(self):
        name = "ExampleSite"
        url = "https://foo.bar"
        is_active = True
        records = [
            {
                "full_name": name,
                "url": url,
                "is_active": is_active,
            },
        ]

        task = create_task(AddRemoteSiteSettings, {"records": records})
        with TemporaryDirectory() as tempdir:
            task.deploy_dir = Path(tempdir)
            task._synthesize()

            rss_xml_file = Path(f"{tempdir}/{RSS_DIR_NAME}/{name}.{RSS_FILE_EXTENSION}")
            assert rss_xml_file.is_file()

            file_content = rss_xml_file.read_text()
            dom = parseString(file_content)

            assert url == get_node_value("url", dom)
            assert "" == get_node_value("description", dom)
            assert is_active == bool(get_node_value("isActive", dom))


def get_node_value(tag_name: str, dom) -> str:
    element = dom.getElementsByTagName(tag_name)[0]
    if element.firstChild:
        return element.firstChild.nodeValue
    return ""
