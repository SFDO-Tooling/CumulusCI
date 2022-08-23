from typing import List, Optional

import pydantic
from pydantic import BaseModel

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl.base import BaseMetadataSynthesisTask

REQUIRED_FIELD_ERR = "You must specify a value for RemoteSiteSetting.{} on all entries."
RSS_DIR_NAME = "remoteSiteSettings"
RSS_FILE_EXTENSION = "remoteSite"
RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<RemoteSiteSetting xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>{description}</description>
    <disableProtocolSecurity>{disable_protocol_security}</disableProtocolSecurity>
    <isActive>{is_active}</isActive>
    <url>{url}</url>
</RemoteSiteSetting>"""


class RemoteSiteSetting(BaseModel):
    """Schema for the RemoteSiteSetting object"""

    full_name: str
    url: str
    is_active: bool
    description: Optional[str]
    disable_protocol_security: Optional[bool]


class RSSOptions(BaseModel):
    """Defines the options for this task"""

    records: List[RemoteSiteSetting]


class AddRemoteSiteSettings(BaseMetadataSynthesisTask):
    """Task for adding Remote Site Setting records to an org"""

    entity = "RemoteSiteSetting"
    task_docs = """

        Example Usage
        -----------------------

        .. code-block::  yaml

            task: add_remote_site_settings
            options:
                records:
                    - full_name: ExampleRemoteSiteSetting
                      description: Descriptions can be included optionally
                      url: https://test.salesforce.com
                      is_active: True

    """
    task_options = {
        "records": {
            "description": "Array of RemoteSiteSetting records to insert. "
            "Each RemoteSiteSetting requires the keys: 'full_name', 'is_active', and 'url'. "
            "'description' is optional, and defaults to an empty string. "
            "'disable_security_protocol' is optional, and defaults to False.",
            "required": True,
        },
    }

    def _synthesize(self):
        options: RSSOptions = self._get_options()
        for rss in options.records:
            content: str = self._get_rss_xml_content(rss)
            filename: str = f"{rss.full_name}.{RSS_FILE_EXTENSION}"
            self._create_rss_file(filename, content)
        return

    def _get_options(self) -> RSSOptions:
        """Parse and return the options defined in RSSOptions"""
        try:
            return RSSOptions.parse_obj(self.options)
        except pydantic.ValidationError as exc:
            raise TaskOptionsError(f"Invalid options: {exc}")

    def _get_rss_xml_content(self, rss: RemoteSiteSetting) -> str:
        disable_protocol_security = rss.disable_protocol_security or False
        is_active = rss.is_active or False
        return RSS_XML.format(
            url=rss.url,
            is_active=is_active,
            description=rss.description or "",
            disable_protocol_security=disable_protocol_security,
        )

    def _create_rss_file(self, filename: str, content: str):
        """Creates an xml file with given name and contents in self.deploy_dir/RemoteSiteSettings/"""
        rss_dir = self.deploy_dir / RSS_DIR_NAME
        rss_dir.mkdir(exist_ok=True)

        filepath = rss_dir / filename
        filepath.touch(exist_ok=False)
        filepath.write_text(content, encoding="UTF-8")
