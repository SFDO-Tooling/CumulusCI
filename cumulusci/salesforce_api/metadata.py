'''
python interface to the Salesforce Metadata API
based on mrbelvedere/mpinstaller/mdapi.py
'''

# TO DO
#   - add docstrings
#   - parse dates from SOAP response
#   - use format() instead of %

import base64
# import dateutil.parser
import httplib
import re
from tempfile import TemporaryFile
import time
from xml.dom.minidom import parseString
from zipfile import ZipFile

import requests

from cumulusci.salesforce_api import soap_envelopes
from cumulusci.salesforce_api.exceptions import MetadataApiError


class BaseMetadataApiCall(object):
    check_interval = 1
    soap_envelope_start = None
    soap_envelope_status = None
    soap_envelope_result = None
    soap_action_start = None
    soap_action_status = None
    soap_action_result = None

    def __init__(self, task):
        # the cumulucci context object contains logger, oauth, ID, secret, etc
        self.task = task
        self.status = None

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
        endpoint = '%s/services/Soap/m/33.0/%s' % (instance_url, org_id)
        return endpoint

    def _build_envelope_result(self):
        if self.soap_envelope_result:
            return self.soap_envelope_result % {'process_id': self.process_id}

    def _build_envelope_start(self):
        if self.soap_envelope_start:
            return self.soap_envelope_start

    def _build_envelope_status(self):
        if self.soap_envelope_status:
            return self.soap_envelope_status % {'process_id': self.process_id}

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
        if result:
            return result[0].firstChild.nodeValue

    def _get_response(self):
        if not self.soap_envelope_start:
            # where is this from?
            raise NotImplemented('No soap_start template was provided')
        # Start the call
        envelope = self._build_envelope_start()
        if not envelope:
            return
        envelope = envelope.encode('utf-8')
        headers = self._build_headers(self.soap_action_start, envelope)
        response = self._call_mdapi(headers, envelope)
        # If no status or result calls are configured, return the result
        if not self.soap_envelope_status and not self.soap_envelope_result:
            return response
        # Process the response to set self.process_id with the process id
        # started
        response = self._process_response_start(response)
        # Check the status if configured
        if self.soap_envelope_status:
            while self.status not in ['Done', 'Failed']:
                # Check status in a loop until done
                envelope = self._build_envelope_status()
                if not envelope:
                    return
                envelope = envelope.encode('utf-8')
                headers = self._build_headers(
                    self.soap_action_status, envelope)
                response = self._call_mdapi(headers, envelope)
                response = self._process_response_status(response)
                time.sleep(self.check_interval)
            # Fetch the final result and return
            if self.soap_envelope_result:
                envelope = self._build_envelope_result()
                if not envelope:
                    return
                envelope = envelope.encode('utf-8')
                headers = self._build_headers(
                    self.soap_action_result, envelope)
                response = self._call_mdapi(headers, envelope)
            else:
                return response
        else:
            # Check the result and return when done
            while self.status not in ['Succeeded', 'Failed', 'Cancelled']:
                time.sleep(self.check_interval)
                envelope = self._build_envelope_result()
                envelope = envelope.encode('utf-8')
                headers = self._build_headers(
                    self.soap_action_result, envelope)
                response = self._call_mdapi(headers, envelope)
                response = _process_response_result(response)
        return response

    def _handle_soap_error(self, headers, envelope, refresh, response):
        faultcode = parseString(
            response.content).getElementsByTagName('faultcode')
        if faultcode:
            faultcode = faultcode[0].firstChild.nodeValue
        else:
            faultcode = ''
        faultstring = parseString(
            response.content).getElementsByTagName('faultstring')
        if faultstring:
            faultstring = faultstring[0].firstChild.nodeValue
        else:
            faultstring = response.content
        if faultcode == 'sf:INVALID_SESSION_ID' and self.task.org_config and self.task.org_config.refresh_token:
            # Attempt to refresh token and recall request
            if refresh:
                self.org_config.refresh_oauth_token()
                return self._call_mdapi(headers, envelope, refresh=False)
        # Log the error
        message = '{}: {}'.format(faultcode, faultstring)
        self._set_status('Failed', message)
        raise MetadataApiError(message, response)

    def _process_response(self, response):
        return response

    def _process_response_result(self, response):
        self._set_status('Succeeded')
        return response

    def _process_response_start(self, response):
        if response.status_code == httplib.INTERNAL_SERVER_ERROR:
            return response
        ids = parseString(response.content).getElementsByTagName('id')
        if ids:
            self.process_id = ids[0].firstChild.nodeValue
        return response

    def _process_response_status(self, response):
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

        if level == 'error':
            raise MetadataApiError(log, response)


class ApiRetrieveUnpackaged(BaseMetadataApiCall):
    check_interval = 1
    soap_envelope_start = soap_envelopes.RETRIEVE_UNPACKAGED
    soap_envelope_status = soap_envelopes.CHECK_STATUS
    soap_envelope_result = soap_envelopes.CHECK_RETRIEVE_STATUS
    soap_action_start = 'retrieve'
    soap_action_status = 'checkStatus'
    soap_action_result = 'checkRetrieveStatus'

    def __init__(self, task, package_xml, api_version):
        super(ApiRetrieveUnpackaged, self).__init__(task)
        self.package_xml = package_xml
        self.api_version = api_version
        self._clean_package_xml()

    def _clean_package_xml(self):
        self.package_xml = re.sub('<\?xml.*\?>', '', self.package_xml)
        self.package_xml = re.sub('<Package.*>', '', self.package_xml, 1)
        self.package_xml = re.sub('</Package>', '', self.package_xml, 1)
        self.package_xml = re.sub('\n', '', self.package_xml)
        self.package_xml = re.sub(' *', '', self.package_xml)

    def _build_envelope_start(self):
        return self.soap_envelope_start.format(
            self.api_version,
            self.package_xml,
        )

    def _process_response(self, response):
        # Parse the metadata zip file from the response
        zipstr = parseString(response.content).getElementsByTagName('zipFile')
        if zipstr:
            zipstr = zipstr[0].firstChild.nodeValue
        else:
            return self.packages
        zipfp = TemporaryFile()
        zipfp.write(base64.b64decode(zipstr))
        zipfile = ZipFile(zipfp, 'r')
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
        self.packages = []

    def _process_response(self, response):
        # Parse the metadata zip file from the response
        zipstr = parseString(response.content).getElementsByTagName('zipFile')
        if zipstr:
            zipstr = zipstr[0].firstChild.nodeValue
        else:
            return self.packages
        zipfp = TemporaryFile()
        zipfp.write(base64.b64decode(zipstr))
        zipfile = ZipFile(zipfp, 'r')
        packages = {}
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
            packages[namespace] = version
        self.packages = packages
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
        super(ApiRetrievePackaged, self).__init__(task)
        self.package_name = package_name
        self.api_version = api_version

    def _build_envelope_start(self):
        return self.soap_envelope_start.format(
            self.api_version,
            self.package_name,
        )

    def _process_response(self, response):
        # Parse the metadata zip file from the response
        zipstr = parseString(response.content).getElementsByTagName('zipFile')
        if zipstr:
            zipstr = zipstr[0].firstChild.nodeValue
        else:
            return self.packages
        zipfp = TemporaryFile()
        zipfp.write(base64.b64decode(zipstr))
        zipfile = ZipFile(zipfp, 'r')
        return zipfile


class ApiDeploy(BaseMetadataApiCall):
    soap_envelope_start = soap_envelopes.DEPLOY
    soap_envelope_status = soap_envelopes.CHECK_DEPLOY_STATUS
    soap_action_start = 'deploy'
    soap_action_status = 'checkDeployStatus'

    def __init__(self, task, package_zip, purge_on_delete=True):
        super(ApiDeploy, self).__init__(task)
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
            return self.soap_envelope_start % {
                'package_zip': self.package_zip,
                'purge_on_delete': self.purge_on_delete,
            }

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
            # If failed, parse out the problem text and set as the log
            problems = parseString(
                response.content).getElementsByTagName('problem')
            messages = []
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
                    message.append('from namespace %s: ' % namespace)
                if stacktrace:
                    message.append(stacktrace)
                messages.append(''.join(message))
            if messages:
                log = '\n\n'.join(messages)
            else:
                log = response.content
            self._set_status('Failed', log)
        return self.status


class ApiInstallVersion(ApiDeploy):

    def __init__(self, task, version, purge_on_delete=False):
        self.version = version
        # Construct and set the package_zip file
        if self.version.number:
            self.package_zip = PackageZipBuilder(
                self.version.package.namespace, self.version.number).install_package()
        elif self.version.zip_url or self.version.repo_url:
            if self.version.repo_url:
                repo_url = self.version.repo_url
                git_ref = self.version.branch
                if installation_step.installation.git_ref:
                    git_ref = installation_step.installation.git_ref
                if installation_step.installation.fork:
                    repo_url_parts = repo_url.split('/')
                    repo_url_parts[3] = installation_step.installation.fork
                    repo_url = '/'.join(repo_url_parts)
                zip_url = '%s/archive/%s.zip' % (repo_url, git_ref)
            else:
                zip_url = self.version.zip_url
            # Deploy a zipped bundled downloaded from a URL
            try:
                zip_resp = requests.get(zip_url)
            except:
                raise ValueError('Failed to fetch zip from %s' %
                                 self.version.zip_url)
            zipfp = TemporaryFile()
            zipfp.write(zip_resp.content)
            zipfile = ZipFile(zipfp, 'r')
            if not self.version.subfolder and not self.version.repo_url:
                zipfile.close()
                zipfp.seek(0)
                self.package_zip = base64.b64encode(zipfp.read())
            else:
                ignore_prefix = ''
                if self.version.repo_url:
                    # Get the top level folder from the zip
                    ignore_prefix = '%s/' % zipfile.namelist()[0].split('/')[0]
                # Extract a subdirectory from the zip
                subdirectory = ignore_prefix + self.version.subfolder
                subzip = zip_subfolder(
                    zipfile, subdirectory, self.version.namespace_token, self.version.namespace)
                subzipfp = subzip.fp
                subzip.close()
                subzipfp.seek(0)
                self.package_zip = base64.b64encode(subzipfp.read())
        super(ApiInstallVersion, self).__init__(
            task, self.package_zip, purge_on_delete)


class ApiUninstallVersion(ApiDeploy):

    def __init__(self, task, version, purge_on_delete=True):
        self.version = version
        if not version.number:
            self.package_zip = None
        else:
            self.package_zip = PackageZipBuilder(
                self.version.package.namespace).uninstall_package()
        super(ApiUninstallVersion, self).__init__(
            task, self.package_zip, purge_on_delete)


class ApiListMetadata(BaseMetadataApiCall):
    soap_envelope_start = soap_envelopes.LIST_METADATA
    soap_action_start = 'listMetadata'

    def __init__(self, task, metadata_type, metadata):
        super(ApiListMetadata, self).__init__(task)
        self.metadata_type = metadata_type
        self.metadata = metadata

    def _build_envelope_start(self):
        return self.soap_envelope_start % {'metadata_type': self.metadata_type}

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
        self.metadata[self.metadata_type] = metadata
        return metadata
