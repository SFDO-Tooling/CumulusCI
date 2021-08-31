CREATE_SUBSCRIBER_ATTRIBUTE = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:a="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:u="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
<s:Header>
  <a:Action s:mustUnderstand="1">Configure</a:Action>
  <a:To s:mustUnderstand="1">{soap_instance_url}Service.asmx</a:To>
  <fueloauth>{access_token}</fueloauth>
</s:Header>
<s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <ConfigureRequestMsg xmlns="http://exacttarget.com/wsdl/partnerAPI">
    <Options></Options>
    <Action>Create</Action>
    <Configurations>
      <Configuration xsi:type="PropertyDefinition">
        <PartnerKey xsi:nil="true"></PartnerKey>
        <ObjectID xsi:nil="true"></ObjectID>
        <Name>{attribute_name}</Name>
        <PropertyType>string</PropertyType>
      </Configuration>
    </Configurations>
  </ConfigureRequestMsg>
</s:Body>
</s:Envelope>"""
