CREATE_SUBSCRIBER_ATTRIBUTE_EXPECTED_SOAP_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"
    xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
    xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <env:Header xmlns:env="http://www.w3.org/2003/05/soap-envelope">
        <wsa:Action>ConfigureResponse</wsa:Action>
        <wsa:MessageID>urn:uuid:9be492dc-a0b9-4cf9-908b-e02a11d623c3</wsa:MessageID>
        <wsa:RelatesTo>urn:uuid:b7df082c-4ddb-4a62-8cda-de290f42b9c0</wsa:RelatesTo>
        <wsa:To>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:To>
        <wsse:Security>
            <wsu:Timestamp wsu:Id="Timestamp-61ba3507-784d-4084-bdf0-0ca052fc29ec">
                <wsu:Created>2021-08-30T19:24:48Z</wsu:Created>
                <wsu:Expires>2021-08-30T19:29:48Z</wsu:Expires>
            </wsu:Timestamp>
        </wsse:Security>
    </env:Header>
    <soap:Body>
        <ConfigureResponseMsg xmlns="http://exacttarget.com/wsdl/partnerAPI">
            <Results>
                <Result>
                    <StatusCode>OK</StatusCode>
                    <StatusMessage>Success</StatusMessage>
                    <OrdinalID>0</OrdinalID>
                    <Object xsi:type="PropertyDefinition">
                        <PartnerKey xsi:nil="true" />
                        <ID>126713</ID>
                        <ObjectID xsi:nil="true" />
                        <Name>Test Subscriber Attribute</Name>
                        <PropertyType>string</PropertyType>
                    </Object>
                </Result>
            </Results>
            <OverallStatus>OK</OverallStatus>
            <OverallStatusMessage />
            <RequestID>ef959dde-a21d-46ac-b2de-98d9e656ed6f</RequestID>
        </ConfigureResponseMsg>
    </soap:Body>
</soap:Envelope>"""

CREATE_USER_EXPECTED_SOAP_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <env:Header xmlns:env="http://www.w3.org/2003/05/soap-envelope">
        <wsa:Action>CreateResponse</wsa:Action>
        <wsa:MessageID>urn:uuid:73668493-d031-493c-b291-7fffe3bf46d0</wsa:MessageID>
        <wsa:RelatesTo>urn:uuid:9367afcb-c4ec-48f8-9a6f-2d0de4e37dff</wsa:RelatesTo>
        <wsa:To>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:To>
        <wsse:Security>
            <wsu:Timestamp wsu:Id="Timestamp-c58859fa-815f-4ecb-b278-d8df5249e0e6">
                <wsu:Created>2021-08-31T06:10:52Z</wsu:Created>
                <wsu:Expires>2021-08-31T06:15:52Z</wsu:Expires>
            </wsu:Timestamp>
        </wsse:Security>
    </env:Header>
    <soap:Body>
        <CreateResponse xmlns="http://exacttarget.com/wsdl/partnerAPI">
            <Results>
                <StatusCode>OK</StatusCode>
                <StatusMessage>Account User Updated / Created</StatusMessage>
                <OrdinalID>0</OrdinalID>
                <NewID>0</NewID>
                <Object xsi:type="AccountUser">
                    <Client>
                        <ID>523005197</ID>
                    </Client>
                    <PartnerKey xsi:nil="true" />
                    <ID>722602484</ID>
                    <ObjectID xsi:nil="true" />
                    <CustomerKey>Don_Draper_Key_1926</CustomerKey>
                    <UserID>sterling-don</UserID>
                    <Password />
                    <Name>Don Draper</Name>
                    <Email>don.draper@sterlingcooper.com</Email>
                    <UserPermissions>
                        <PartnerKey xsi:nil="true" />
                        <ID>31</ID>
                        <ObjectID xsi:nil="true" />
                        <Name xsi:nil="true" />
                        <Value xsi:nil="true" />
                        <Description xsi:nil="true" />
                        <Delete>0</Delete>
                    </UserPermissions>
                    <Delete>0</Delete>
                    <IsAPIUser>true</IsAPIUser>
                    <DefaultBusinessUnit>523008403</DefaultBusinessUnit>
                </Object>
            </Results>
            <RequestID>09647ed9-38d4-4431-9fa2-ae29df011a5a</RequestID>
            <OverallStatus>OK</OverallStatus>
        </CreateResponse>
    </soap:Body>
</soap:Envelope>"""

UPDATE_USER_ROLE_EXPECTED_SOAP_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <env:Header xmlns:env="http://www.w3.org/2003/05/soap-envelope">
        <wsa:Action>CreateResponse</wsa:Action>
        <wsa:MessageID>urn:uuid:ed9644d9-3258-4799-899a-0fef9503d6b9</wsa:MessageID>
        <wsa:RelatesTo>urn:uuid:eaea2d53-ecf4-4ddc-b0c6-aa690d4141b1</wsa:RelatesTo>
        <wsa:To>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:To>
        <wsse:Security>
            <wsu:Timestamp wsu:Id="Timestamp-ee6031ae-b715-4ea0-a246-7607c807b830">
                <wsu:Created>2021-08-31T06:03:37Z</wsu:Created>
                <wsu:Expires>2021-08-31T06:08:37Z</wsu:Expires>
            </wsu:Timestamp>
        </wsse:Security>
    </env:Header>
    <soap:Body>
        <UpdateResponse xmlns="http://exacttarget.com/wsdl/partnerAPI">
            <Results>
                <StatusCode>OK</StatusCode>
                <StatusMessage>Account User Updated / Created</StatusMessage>
                <OrdinalID>0</OrdinalID>
                <Object xsi:type="AccountUser">
                    <Client>
                        <ID>523005197</ID>
                    </Client>
                    <PartnerKey xsi:nil="true" />
                    <ID>722602484</ID>
                    <ObjectID xsi:nil="true" />
                    <CustomerKey>Don_Draper_Key_1926</CustomerKey>
                    <AccountUserID>722602484</AccountUserID>
                    <Password />
                    <Name>Partner Don Draper</Name>
                    <Email>don.draper@sterlingcooper.com</Email>
                    <UserPermissions>
                        <PartnerKey xsi:nil="true" />
                        <ID>31</ID>
                        <ObjectID xsi:nil="true" />
                        <Name xsi:nil="true" />
                        <Value xsi:nil="true" />
                        <Description xsi:nil="true" />
                        <Delete>0</Delete>
                    </UserPermissions>
                    <Delete>0</Delete>
                    <IsAPIUser>true</IsAPIUser>
                </Object>
            </Results>
            <RequestID>37ee797a-12ae-4d99-8294-c9f3451c5cd5</RequestID>
            <OverallStatus>OK</OverallStatus>
        </UpdateResponse>
    </soap:Body>
</soap:Envelope>"""
