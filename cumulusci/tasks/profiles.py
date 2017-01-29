''' Profiles offers a module for modifying profiles in an org to a YAML specification.

Based on a simple YAML file definition for a profile or permission set, Profiles will
retrieve the relevant metadata from an org, update the profile settings as you define,
and then push the update to the org.

Stop keeping thousands of lines of permission sets in your source control when they only
add one field. Make your code meaningful.
'''

import StringIO
import zipfile

from xml.etree.ElementTree import ElementTree

from cumulusci.core.tasks import BaseTask
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.tasks.salesforce import BaseSalesforceMetadataApiTask

