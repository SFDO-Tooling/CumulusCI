DEPLOY = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <SessionHeader xmlns="http://soap.sforce.com/2006/04/metadata">
      <sessionId>###SESSION_ID###</sessionId>
    </SessionHeader>
  </soap:Header>
  <soap:Body>
    <deploy xmlns="http://soap.sforce.com/2006/04/metadata">
      <ZipFile>{package_zip}</ZipFile>
      <DeployOptions>
        <allowMissingFiles>false</allowMissingFiles>
        <autoUpdatePackage>false</autoUpdatePackage>
        <checkOnly>{check_only}</checkOnly>
        <ignoreWarnings>true</ignoreWarnings>
        <performRetrieve>false</performRetrieve>
        <purgeOnDelete>{purge_on_delete}</purgeOnDelete>
        <rollbackOnError>true</rollbackOnError>
        <runAllTests>false</runAllTests>
        <singlePackage>true</singlePackage>
        {test_level}
        {run_tests}
      </DeployOptions>
    </deploy>
  </soap:Body>
</soap:Envelope>"""

CHECK_DEPLOY_STATUS = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <SessionHeader xmlns="http://soap.sforce.com/2006/04/metadata">
      <sessionId>###SESSION_ID###</sessionId>
    </SessionHeader>
  </soap:Header>
  <soap:Body>
    <checkDeployStatus xmlns="http://soap.sforce.com/2006/04/metadata">
      <asyncProcessId>{process_id}</asyncProcessId>
      <includeDetails>true</includeDetails>
    </checkDeployStatus>
  </soap:Body>
</soap:Envelope>"""

RETRIEVE_INSTALLEDPACKAGE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <SessionHeader xmlns="http://soap.sforce.com/2006/04/metadata">
      <sessionId>###SESSION_ID###</sessionId>
    </SessionHeader>
  </soap:Header>
  <soap:Body>
    <retrieve xmlns="http://soap.sforce.com/2006/04/metadata">
      <retrieveRequest>
        <apiVersion>{api_version}</apiVersion>
        <unpackaged>
          <types>
            <members>*</members>
            <name>InstalledPackage</name>
          </types>
          <version>{api_version}</version>
        </unpackaged>
      </retrieveRequest>
    </retrieve>
  </soap:Body>
</soap:Envelope>"""

RETRIEVE_PACKAGED = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <SessionHeader xmlns="http://soap.sforce.com/2006/04/metadata">
      <sessionId>###SESSION_ID###</sessionId>
    </SessionHeader>
  </soap:Header>
  <soap:Body>
    <retrieve xmlns="http://soap.sforce.com/2006/04/metadata">
      <retrieveRequest>
        <apiVersion>{api_version}</apiVersion>
        <packageNames>{package_name}</packageNames>
      </retrieveRequest>
    </retrieve>
  </soap:Body>
</soap:Envelope>"""

RETRIEVE_UNPACKAGED = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <SessionHeader xmlns="http://soap.sforce.com/2006/04/metadata">
      <sessionId>###SESSION_ID###</sessionId>
    </SessionHeader>
  </soap:Header>
  <soap:Body>
    <retrieve xmlns="http://soap.sforce.com/2006/04/metadata">
      <retrieveRequest>
        <apiVersion>{api_version}</apiVersion>
        <unpackaged>
          {package_xml}
        </unpackaged>
      </retrieveRequest>
    </retrieve>
  </soap:Body>
</soap:Envelope>"""

LIST_METADATA = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <SessionHeader xmlns="http://soap.sforce.com/2006/04/metadata">
      <sessionId>###SESSION_ID###</sessionId>
    </SessionHeader>
  </soap:Header>
  <soap:Body>
    <listMetadata xmlns="http://soap.sforce.com/2006/04/metadata">
      <queries>
        <type>{metadata_type}</type>{folder}
      </queries>
      <asOfVersion>{as_of_version}</asOfVersion>
    </listMetadata>
  </soap:Body>
</soap:Envelope>"""

CHECK_STATUS = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <SessionHeader xmlns="http://soap.sforce.com/2006/04/metadata">
      <sessionId>###SESSION_ID###</sessionId>
    </SessionHeader>
  </soap:Header>
  <soap:Body>
    <checkStatus xmlns="http://soap.sforce.com/2006/04/metadata">
      <asyncProcessId>{process_id}</asyncProcessId>
    </checkStatus>
  </soap:Body>
</soap:Envelope>"""

CHECK_RETRIEVE_STATUS = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <SessionHeader xmlns="http://soap.sforce.com/2006/04/metadata">
      <sessionId>###SESSION_ID###</sessionId>
    </SessionHeader>
  </soap:Header>
  <soap:Body>
    <checkRetrieveStatus xmlns="http://soap.sforce.com/2006/04/metadata">
      <asyncProcessId>{process_id}</asyncProcessId>
    </checkRetrieveStatus>
  </soap:Body>
</soap:Envelope>"""

CREATE_PROFILE = """<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:partner.soap.sforce.com" xmlns:urn1="urn:sobject.partner.soap.sforce.com">
  <soapenv:Header>
    <urn:SessionHeader>
      <urn:sessionId>###SESSION_ID###</urn:sessionId>
    </urn:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <urn:create>
      <urn:sObjects xsi:type="urn1:Profile" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <Name>{name}</Name>
        <Description>{description}</Description>
        <UserLicenseId>{license_id}</UserLicenseId>
      </urn:sObjects>
    </urn:create>
  </soapenv:Body>
</soapenv:Envelope>"""

DESCRIBE_METADATA = """<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="http://soap.sforce.com/2006/04/metadata">
  <soapenv:Header>
    <tns:SessionHeader>
      <tns:sessionId>###SESSION_ID###</tns:sessionId>
    </tns:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <tns:describeMetadata>
      <asOfVersion>{api_version}</asOfVersion>
    </tns:describeMetadata>
  </soapenv:Body>
</soapenv:Envelope>"""
