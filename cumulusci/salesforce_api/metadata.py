'''
python interface to the Salesforce Metadata API
based on mrbelvedere/mpinstaller/mdapi.py
'''

# TO DO
#   - add docstrings
#   - parse dates from SOAP response
#   - use format() instead of %
#   - look at https://github.com/rholder/retrying

from __future__ import unicode_literals
import base64
# import dateutil.parser
import httplib
import re
import time
from xml.dom.minidom import parseString
from xml.sax.saxutils import escape
from zipfile import ZipFile
import StringIO

import requests

from cumulusci.salesforce_api import soap_envelopes
from cumulusci.core.exceptions import ApexTestException
from cumulusci.utils import zip_subfolder
from cumulusci.salesforce_api.exceptions import MetadataComponentFailure
from cumulusci.salesforce_api.exceptions import MetadataApiError


class BaseMetadataApiCall(object):
    check_interval = 1
    soap_envelope_start = None
    soap_envelope_status = None
    soap_envelope_result = None
    soap_action_start = None
    soap_action_status = None
    soap_action_result = None

    def __init__(self, task, api_version=None):
        # the cumulucci context object contains logger, oauth, ID, secret, etc
        self.task = task
        self.status = None
        self.check_num = 1
        self.api_version = (
            api_version if api_version else
            task.project_config.project__package__api_version
        )

    def __call__(self):
        self.task.logger.info('Pending')
        response = self._get_response()
        if self.status != 'Failed':
            return self._process_response(response)

    def _build_endpoint_url(self):
        # Parse org id from id which ends in /ORGID/USERID
        org_id = self.task.org_config.org_id
        # If "My Domain" is configured in the org, the instance_url needs to be
        # parsed differently
        instance_url = self.task.org_config.instance_url
        if instance_url.find('.my.salesforce.com') != -1:
            # Parse instance_url with My Domain configured
            # URL will be in the format
            # https://name--name.na11.my.salesforce.com and should be
            # https://na11.salesforce.com
            instance_url = re.sub(
                r'https://.*\.(\w+)\.my\.salesforce\.com', r'https://\1.salesforce.com', instance_url)
        # Build the endpoint url from the instance_url
        endpoint = '{}/services/Soap/m/{}/{}'.format(
            instance_url,
            self.api_version,
            org_id,
        )
        return endpoint

    def _build_envelope_result(self):
        if self.soap_envelope_result:
            return self.soap_envelope_result.format(
                process_id = self.process_id
            )

    def _build_envelope_start(self):
        if self.soap_envelope_start:
            return self.soap_envelope_start.format(
                api_version=self.api_version,
            )

    def _build_envelope_status(self):
        if self.soap_envelope_status:
            return self.soap_envelope_status.format(
                process_id = self.process_id
            )

    def _build_headers(self, action, message):
        return {
            'Content-Type': 'text/xml; charset=UTF-8',
            'Content-Length': str(len(message)),
            'SOAPAction': action,
        }

    def _call_mdapi(self, headers, envelope, refresh=None):
        # Insert the session id
        session_id = self.task.org_config.access_token
        auth_envelope = envelope.replace('###SESSION_ID###', session_id)
        response = requests.post(self._build_endpoint_url(
        ), headers=headers, data=auth_envelope)
        faultcode = parseString(
            response.content).getElementsByTagName('faultcode')
        # refresh = False can be passed to prevent a loop if refresh fails
        if refresh is None:
            refresh = True
        if faultcode:
            return self._handle_soap_error(headers, envelope, refresh, response)
        return response

    def _get_element_value(self, dom, tag):
        result = dom.getElementsByTagName(tag)
        if result and result[0].firstChild:
            return result[0].firstChild.nodeValue

    def _get_check_interval(self):
        return self.check_interval * ((self.check_num / 3) + 1)

    def _get_response(self):
        if not self.soap_envelope_start:
            raise NotImplementedError('No soap_start template was provided')
        # Start the call
        envelope = self._build_envelope_start()
        envelope = envelope.encode('utf-8')
        headers = self._build_headers(self.soap_action_start, envelope)
        response = self._call_mdapi(headers, envelope)
        # If no status envelope is configured, return the response directly
        if not self.soap_envelope_status:
            return response
        # Process the response to set self.process_id with the process id
        # started
        response = self._process_response_start(response)
        # Check the status if configured
        if self.soap_envelope_status:
            while self.status not in ['Done', 'Failed']:
                # Check status in a loop until done
                envelope = self._build_envelope_status()
                envelope = envelope.encode('utf-8')
                headers = self._build_headers(
                    self.soap_action_status, envelope)
                response = self._call_mdapi(headers, envelope)
                response = self._process_response_status(response)

                # start increasing the check interval progressively to handle long pending jobs
                check_interval = self._get_check_interval()
                self.check_num += 1

                time.sleep(check_interval)
            # Fetch the final result and return
            if self.soap_envelope_result:
                envelope = self._build_envelope_result()
                envelope = envelope.encode('utf-8')
                headers = self._build_headers(
                    self.soap_action_result, envelope)
                response = self._call_mdapi(headers, envelope)
            else:
                return response
        return response

    def _handle_soap_error(self, headers, envelope, refresh, response):
        faultcode = parseString(
            response.content).getElementsByTagName('faultcode')
        if faultcode:
            faultcode = faultcode[0].firstChild.nodeValue
        faultstring = parseString(
            response.content).getElementsByTagName('faultstring')
        if faultstring:
            faultstring = faultstring[0].firstChild.nodeValue
        else:
            faultstring = response.content
        if faultcode == 'sf:INVALID_SESSION_ID' and self.task.org_config and self.task.org_config.refresh_token:
            # Attempt to refresh token and recall request
            if refresh:
                self.task.org_config.refresh_oauth_token()
                return self._call_mdapi(headers, envelope, refresh=False)
        # Log the error
        message = '{}: {}'.format(faultcode, faultstring)
        self._set_status('Failed', message)
        raise MetadataApiError(message, response)

    def _process_response(self, response):
        return response.content

    def _process_response_start(self, response):
        if response.status_code == httplib.INTERNAL_SERVER_ERROR:
            raise MetadataApiError('HTTP ERROR {}: {}'.format(response.status_code, response.content), response)
        ids = parseString(response.content).getElementsByTagName('id')
        if ids:
            self.process_id = ids[0].firstChild.nodeValue
        return response

    def _process_response_status(self, response):
        if response.status_code == httplib.INTERNAL_SERVER_ERROR:
            raise MetadataApiError('HTTP ERROR {}: {}'.format(response.status_code, response.content), response)
        resp_xml = parseString(response.content)
        done = resp_xml.getElementsByTagName('done')
        if done:
            if done[0].firstChild.nodeValue == 'true':
                self._set_status('Done')
            else:
                state_detail = resp_xml.getElementsByTagName('stateDetail')
                if state_detail:
                    log = state_detail[0].firstChild.nodeValue
                    self._set_status('InProgress', log)
                    self.check_num = 1
                elif self.status == 'InProgress':
                    self.check_num = 1
                    self._set_status('InProgress', 'next check in {} seconds'.format(self._get_check_interval()))
                else:
                    self._set_status('Pending', 'next check in {} seconds'.format(self._get_check_interval()))
        else:
            # If no done element was in the xml, fail logging the entire SOAP
            # envelope as the log
            self._set_status('Failed', response.content, response=response)
        return response

    def _set_status(self, status, log=None, level=None, response=None):
        if not level:
            level = 'info'
            if status == 'Failed':
                level = 'error'
        logger = getattr(self.task.logger, level)
        self.status = status
        if log:
            logger('[{}]: {}'.format(status, log))
        else:
            logger('[{}]'.format(status))


class ApiRetrieveUnpackaged(BaseMetadataApiCall):
    check_interval = 1
    soap_envelope_start = soap_envelopes.RETRIEVE_UNPACKAGED
    soap_envelope_status = soap_envelopes.CHECK_STATUS
    soap_envelope_result = soap_envelopes.CHECK_RETRIEVE_STATUS
    soap_action_start = 'retrieve'
    soap_action_status = 'checkStatus'
    soap_action_result = 'checkRetrieveStatus'

    def __init__(self, task, package_xml, api_version):
        super(ApiRetrieveUnpackaged, self).__init__(task, api_version)
        self.package_xml = package_xml
        self._clean_package_xml()

    def _clean_package_xml(self):
        self.package_xml = re.sub('<\?xml.*\?>', '', self.package_xml)
        self.package_xml = re.sub('<Package.*>', '', self.package_xml, 1)
        self.package_xml = re.sub('</Package>', '', self.package_xml, 1)
        self.package_xml = re.sub('\n', '', self.package_xml)
        self.package_xml = re.sub(' +<', '<', self.package_xml)

    def _build_envelope_start(self):
        return self.soap_envelope_start.format(
            api_version = self.api_version,
            package_xml = self.package_xml,
        )

    def _process_response(self, response):
        # Parse the metadata zip file from the response
        zipstr = parseString(response.content).getElementsByTagName('zipFile')
        if zipstr:
            zipstr = zipstr[0].firstChild.nodeValue
        zipstringio = StringIO.StringIO(base64.b64decode(zipstr))
        zipfile = ZipFile(zipstringio, 'r')
        zipfile = zip_subfolder(zipfile, 'unpackaged')
        return zipfile

class ApiRetrieveInstalledPackages(BaseMetadataApiCall):
    check_interval = 1
    soap_envelope_start = soap_envelopes.RETRIEVE_INSTALLEDPACKAGE
    soap_envelope_status = soap_envelopes.CHECK_STATUS
    soap_envelope_result = soap_envelopes.CHECK_RETRIEVE_STATUS
    soap_action_start = 'retrieve'
    soap_action_status = 'checkStatus'
    soap_action_result = 'checkRetrieveStatus'

    def __init__(self, task):
        super(ApiRetrieveInstalledPackages, self).__init__(task)
        self.packages = {}

    def _process_response(self, response):
        # Parse the metadata zip file from the response
        zipstr = parseString(response.content).getElementsByTagName('zipFile')
        if zipstr:
            zipstr = zipstr[0].firstChild.nodeValue
        else:
            return self.packages
        zipstringio = StringIO.StringIO(base64.b64decode(zipstr))
        zipfile = ZipFile(zipstringio, 'r')
        # Loop through all files in the zip skipping anything other than
        # InstalledPackages
        for path in zipfile.namelist():
            if not path.endswith('.installedPackage'):
                continue
            namespace = path.split('/')[-1].split('.')[0]
            version = parseString(zipfile.open(
                path).read()).getElementsByTagName('versionNumber')
            if version:
                version = version[0].firstChild.nodeValue
            self.packages[namespace] = version
        return self.packages


class ApiRetrievePackaged(BaseMetadataApiCall):
    check_interval = 1
    soap_envelope_start = soap_envelopes.RETRIEVE_PACKAGED
    soap_envelope_status = soap_envelopes.CHECK_STATUS
    soap_envelope_result = soap_envelopes.CHECK_RETRIEVE_STATUS
    soap_action_start = 'retrieve'
    soap_action_status = 'checkStatus'
    soap_action_result = 'checkRetrieveStatus'

    def __init__(self, task, package_name, api_version):
        super(ApiRetrievePackaged, self).__init__(task, api_version)
        self.package_name = package_name

    def _build_envelope_start(self):
        return self.soap_envelope_start.format(
            api_version = self.api_version,
            package_name = escape(self.package_name),
        )

    def _process_response(self, response):
        # Parse the metadata zip file from the response
        zipstr = parseString(response.content).getElementsByTagName('zipFile')
        if zipstr:
            zipstr = zipstr[0].firstChild.nodeValue
        zipstringio = StringIO.StringIO(base64.b64decode(zipstr))
        zipfile = ZipFile(zipstringio, 'r')
        return zipfile


class ApiDeploy(BaseMetadataApiCall):
    soap_envelope_start = soap_envelopes.DEPLOY
    soap_envelope_status = soap_envelopes.CHECK_DEPLOY_STATUS
    soap_action_start = 'deploy'
    soap_action_status = 'checkDeployStatus'

    def __init__(self, task, package_zip, purge_on_delete=None, api_version=None):
        super(ApiDeploy, self).__init__(task, api_version)
        if purge_on_delete is None:
            purge_on_delete = True
        self._set_purge_on_delete(purge_on_delete)
        self.package_zip = package_zip

    def _set_purge_on_delete(self, purge_on_delete):
        if purge_on_delete == False or purge_on_delete == 'false':
            self.purge_on_delete = 'false'
        else:
            self.purge_on_delete = 'true'
        # Disable purge on delete entirely for non sandbox or DE orgs as it is
        # not allowed
        # FIXME: To implement this, the task needs to be able to provide the org_type
        #org_type = self.task.org_config.org_type
        #if org_type.find('Sandbox') == -1 and org_type != 'Developer Edition':
        #    self.purge_on_delete = 'false'

    def _build_envelope_start(self):
        if self.package_zip:
            return self.soap_envelope_start .format(
                package_zip = self.package_zip,
                purge_on_delete = self.purge_on_delete,
                api_version = self.api_version,
            )

    def _process_response(self, response):
        status = parseString(response.content).getElementsByTagName('status')
        if status:
            status = status[0].firstChild.nodeValue
        else:
            # If no status element is in the result xml, return fail and log
            # the entire SOAP envelope in the log
            self._set_status('Failed', response.content)
            return self.status
        # Only done responses should be passed so we need to handle any status
        # related to done
        if status in ['Succeeded', 'SucceededPartial']:
            self._set_status('Success', status)
        else:
            # If failed, parse out the problem text and raise appropriate exception
            messages = []
            resp_xml = parseString(response.content)

            component_failures = resp_xml.getElementsByTagName('componentFailures')
            for component_failure in component_failures:
                failure_info = {
                    'component_type': None,
                    'file_name': None,
                    'line_num': None,
                    'column_num': None,
                    'problem': component_failure.getElementsByTagName('problem')[0].firstChild.nodeValue,
                    'problem_type': component_failure.getElementsByTagName('problemType')[0].firstChild.nodeValue,
                }
                component_type = component_failure.getElementsByTagName('componentType')
                if component_type and component_type[0].firstChild:
                    failure_info['component_type'] = component_type[0].firstChild.nodeValue
                file_name = component_failure.getElementsByTagName('fullName')
                if file_name and file_name[0].firstChild:
                    failure_info['file_name'] = file_name[0].firstChild.nodeValue
                if not failure_info['file_name']:
                    file_name = component_failure.getElementsByTagName('fileName')
                    if file_name and file_name[0].firstChild:
                        failure_info['file_name'] = file_name[0].firstChild.nodeValue
        
                line_num = component_failure.getElementsByTagName('lineNumber')
                if line_num and line_num[0].firstChild:
                    failure_info['line_num'] = line_num[0].firstChild.nodeValue
                
                column_num = component_failure.getElementsByTagName('columnNumber')
                if column_num and column_num[0].firstChild:
                    failure_info['column_num'] = column_num[0].firstChild.nodeValue
                
                created = component_failure.getElementsByTagName('created')[0].firstChild.nodeValue == 'true'
                deleted = component_failure.getElementsByTagName('deleted')[0].firstChild.nodeValue == 'true'
                if deleted: 
                    failure_info['action'] = 'Delete'
                elif created:
                    failure_info['action'] = 'Create'
                else:
                    failure_info['action'] = 'Update'
  
                if failure_info['file_name'] and failure_info['line_num']: 
                    messages.append('{action} of {component_type} {file_name}: {problem_type} on line {line_num}, col {column_num}: {problem}'.format(**failure_info))
                elif failure_info['file_name']:
                    messages.append('{action} of {component_type} {file_name}: {problem_type}: {problem}'.format(**failure_info))
                else:
                    messages.append('{action} of {problem_type}: {problem}'.format(**failure_info))

            if messages:
                # Deploy failures due to a component failure should raise MetadataComponentFailure
                log = '\n\n'.join(messages)
                self._set_status('Failed', log)
                raise MetadataComponentFailure(log, response)
                
            else:
                problems = parseString(
                    response.content).getElementsByTagName('problem')
                for problem in problems:
                    messages.append(problem.firstChild.nodeValue)

            # Parse out any failure text (from test failures in production
            # deployments) and add to log
            failures = parseString(
                response.content).getElementsByTagName('failures')
            for failure in failures:
                # Get needed values from subelements
                namespace = failure.getElementsByTagName('namespace')
                if namespace and namespace[0].firstChild:
                    namespace = namespace[0].firstChild.nodeValue
                else:
                    namespace = None
                stacktrace = failure.getElementsByTagName('stackTrace')
                if stacktrace and stacktrace[0].firstChild:
                    stacktrace = stacktrace[0].firstChild.nodeValue
                else:
                    stacktrace = None
                message = ['Apex Test Failure: ', ]
                if namespace:
                    message.append('from namespace {}: '.format(namespace))
                if stacktrace:
                    message.append(stacktrace)
                messages.append(''.join(message))
            if messages:
                log = '\n\n'.join(messages)
            else:
                log = response.content

            if messages:
                # Deploy failures due to a component failure should raise MetadataComponentFailure
                log = '\n\n'.join(messages)
                self._set_status('Failed', log)
                raise ApexTestException(log)

            self._set_status('Failed', log)
            raise MetadataApiError(log, response)

        return self.status


class ApiListMetadata(BaseMetadataApiCall):
    soap_envelope_start = soap_envelopes.LIST_METADATA
    soap_action_start = 'listMetadata'

    def __init__(
                self,
                task,
                metadata_type,
                metadata=None,
                folder=None,
                as_of_version=None
            ):
        super(ApiListMetadata, self).__init__(task)
        self.metadata_type = metadata_type
        self.metadata = metadata
        self.folder = folder
        self.as_of_version = (
            as_of_version if as_of_version else
            task.project_config.project__package__api_version
        )
        self.api_version = self.as_of_version
        if self.metadata is None:
            self.metadata = {}

    def _build_envelope_start(self):
        folder = self.folder
        if folder is None:
            folder = ''
        else:
            folder = '\n      <folder>{}</folder>'.format(folder)      
        return self.soap_envelope_start.format(
            metadata_type=self.metadata_type,
            folder=folder,
            as_of_version=self.as_of_version,
        )

    def _process_response(self, response):
        metadata = []
        tags = [
            'createdById',
            'createdByName',
            'createdDate',
            'fileName',
            'fullName',
            'id',
            'lastModifiedById',
            'lastModifiedByName',
            'lastModifiedDate',
            'manageableState',
            'namespacePrefix',
            'type',
        ]
        # These tags will be interpreted into dates
        parse_dates = [
            'createdDate',
            'lastModifiedDate',
        ]
        for result in parseString(response.content).getElementsByTagName('result'):
            result_data = {}
            # Parse fields
            for tag in tags:
                result_data[tag] = self._get_element_value(result, tag)
            # Parse dates
            # FIXME: This was breaking things
            # for key in parse_dates:
            #    if result_data[key]:
            #        result_data[key] = dateutil.parser.parse(result_data[key])
            metadata.append(result_data)
        if self.metadata_type in self.metadata:
            self.metadata[self.metadata_type].extend(metadata)
        else:
            self.metadata[self.metadata_type] = metadata
        return self.metadata
