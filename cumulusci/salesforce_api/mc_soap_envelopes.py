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

CREATE_USER = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:a="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:u="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <s:Header>
        <a:Action s:mustUnderstand="1">Create</a:Action>
        <a:To s:mustUnderstand="1">{soap_instance_url}Service.asmx</a:To>
        <fueloauth>{access_token}</fueloauth>
    </s:Header>
    <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <CreateRequest xmlns="http://exacttarget.com/wsdl/partnerAPI">
            <Objects xsi:type="AccountUser">
                <ObjectID xsi:nil="true"></ObjectID>
                <!-- REQUIRED: specify the MID for Parent BU -->
                <Client>
                    <ID>{parent_bu_mid}</ID>
                </Client>
                <!-- REQUIRED: Set MID for BU to use as default (can be same as the parent) -->
                <DefaultBusinessUnit>{default_bu_mid}</DefaultBusinessUnit>
                <!-- Set external key for user -->
                {external_key}
                <!-- Set name of user -->
                {user_name}
                <!-- REQUIRED: Set the user email -->
                <Email>{user_email}</Email>
                <NotificationEmailAddress>{user_email}</NotificationEmailAddress>
                <!-- REQUIRED: Set the user password -->
                <Password>{user_password}</Password>
                <!-- REQUIRED: Set the username -->
                <UserID>{user_username}</UserID>
                <IsAPIUser>true</IsAPIUser>
                {active_flag}
                <IsLocked>false</IsLocked>
                <!-- OPTIONAL: Include this if you want to assign roles to new user -->
                <!-- IDs for system defined roles located here: https://developer.salesforce.com/docs/atlas.en-us.noversion.mc-apis.meta/mc-apis/setting_user_permissions_via_the_web_services_api.htm -->
                {role_id}
            </Objects>
        </CreateRequest>
    </s:Body>
</s:Envelope>"""

UPDATE_USER_ROLE = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:a="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:u="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <s:Header>
        <a:Action s:mustUnderstand="1">Create</a:Action>
        <a:To s:mustUnderstand="1">{soap_instance_url}Service.asmx</a:To>
        <fueloauth>{access_token}</fueloauth>
    </s:Header>
    <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <UpdateRequest xmlns="http://exacttarget.com/wsdl/partnerAPI">
            <Objects xsi:type="AccountUser">
                <ObjectID xsi:nil="true"></ObjectID>
                <Client>
                    <ID>{account_mid}</ID> <!-- Account MID -->
                </Client>
                {external_key} <!-- External key for user to update -->
                <IsAPIUser>true</IsAPIUser>
                {user_name}
                <Email>{user_email}</Email>
                <Password>{user_password}</Password>
                <!-- IDs for system defined roles located here: https://developer.salesforce.com/docs/atlas.en-us.noversion.mc-apis.meta/mc-apis/setting_user_permissions_via_the_web_services_api.htm -->
                <UserPermissions>
                    <ID>{role_id}</ID>
                </UserPermissions>
            </Objects>
        </UpdateRequest>
    </s:Body>
</s:Envelope>"""
