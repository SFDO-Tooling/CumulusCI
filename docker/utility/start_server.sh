#!/bin/bash


echo $SFDX_HUB_KEY > /app/sfdx_hub.key
echo "AUTHORIZING SFDX via JWT key auth..."
# authorizing sfdx via jwt key authorization
sfdx force:auth:jwt:grant -u $SFDX_HUB_USERNAME -f /app/sfdx_hub.key -i $SFDX_CLIENT_ID --setdefaultdevhubusername

