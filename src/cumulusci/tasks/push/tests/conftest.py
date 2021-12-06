import pytest

PUSH_FAILURE_RESULT = {
    "totalSize": 10,
    "done": True,
    "records": [
        {
            "attributes": {
                "type": "PackagePushJob",
                "url": "/services/data/v43.0/sobjects/PackagePushJob/0DX1K000000LcuBWAS",
            },
            "Id": "0DX1K000000LcuBWAS",
            "SubscriberOrganizationKey": "00DFeyLoahEKZqo",
            "PackagePushErrors": {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "PackagePushError",
                            "url": "/services/data/v43.0/sobjects/PackagePushError/0DY1K00000013sDWAQ",
                        },
                        "ErrorDetails": None,
                        "ErrorMessage": "This package requires that a newer version of a dependent package be installed before the upgrade can proceed: EDA, Version EDA 1.93.\n\nAsk the subscriber to install the dependent package and then retry the push upgrade.",
                        "ErrorSeverity": "Error",
                        "ErrorTitle": "Dependent Package Conflict",
                        "ErrorType": "IneligibleUpgrade",
                    }
                ],
            },
        },
        {
            "attributes": {
                "type": "PackagePushJob",
                "url": "/services/data/v43.0/sobjects/PackagePushJob/0DX1K000000LcyWWAS",
            },
            "Id": "0DX1K000000LcyWWAS",
            "SubscriberOrganizationKey": "00DhmXPrqbrHoVO",
            "PackagePushErrors": {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "PackagePushError",
                            "url": "/services/data/v43.0/sobjects/PackagePushError/0DY1K00000013sIWAQ",
                        },
                        "ErrorDetails": None,
                        "ErrorMessage": "This package requires that a newer version of a dependent package be installed before the upgrade can proceed: EDA, Version EDA 1.93.\n\nAsk the subscriber to install the dependent package and then retry the push upgrade.",
                        "ErrorSeverity": "Error",
                        "ErrorTitle": "Dependent Package Conflict",
                        "ErrorType": "IneligibleUpgrade",
                    }
                ],
            },
        },
        {
            "attributes": {
                "type": "PackagePushJob",
                "url": "/services/data/v43.0/sobjects/PackagePushJob/0DX1K000000LcvOWAS",
            },
            "Id": "0DX1K000000LcvOWAS",
            "SubscriberOrganizationKey": "00DSZGTJkBGDEsA",
            "PackagePushErrors": {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "PackagePushError",
                            "url": "/services/data/v43.0/sobjects/PackagePushError/0DY1K00000013s3WAA",
                        },
                        "ErrorDetails": None,
                        "ErrorMessage": "This package requires that a newer version of a dependent package be installed before the upgrade can proceed: EDA, Version EDA 1.93.\n\nAsk the subscriber to install the dependent package and then retry the push upgrade.",
                        "ErrorSeverity": "Error",
                        "ErrorTitle": "Dependent Package Conflict",
                        "ErrorType": "IneligibleUpgrade",
                    }
                ],
            },
        },
        {
            "attributes": {
                "type": "PackagePushJob",
                "url": "/services/data/v43.0/sobjects/PackagePushJob/0DX1K000000Lcv5WAC",
            },
            "Id": "0DX1K000000Lcv5WAC",
            "SubscriberOrganizationKey": "00DhEmESVoRAtGA",
            "PackagePushErrors": {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "PackagePushError",
                            "url": "/services/data/v43.0/sobjects/PackagePushError/0DY1K00000013rtWAA",
                        },
                        "ErrorDetails": None,
                        "ErrorMessage": "This package requires that a newer version of a dependent package be installed before the upgrade can proceed: EDA, Version EDA 1.93.\n\nAsk the subscriber to install the dependent package and then retry the push upgrade.",
                        "ErrorSeverity": "Error",
                        "ErrorTitle": "Dependent Package Conflict",
                        "ErrorType": "IneligibleUpgrade",
                    }
                ],
            },
        },
        {
            "attributes": {
                "type": "PackagePushJob",
                "url": "/services/data/v43.0/sobjects/PackagePushJob/0DX1K000000LcxIWAS",
            },
            "Id": "0DX1K000000LcxIWAS",
            "SubscriberOrganizationKey": "00DlwbtJtKxRxQJ",
            "PackagePushErrors": {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "PackagePushError",
                            "url": "/services/data/v43.0/sobjects/PackagePushError/0DY1K00000013srWAA",
                        },
                        "ErrorDetails": None,
                        "ErrorMessage": "This package requires that a newer version of a dependent package be installed before the upgrade can proceed: EDA, Version EDA 1.93.\n\nAsk the subscriber to install the dependent package and then retry the push upgrade.",
                        "ErrorSeverity": "Error",
                        "ErrorTitle": "Dependent Package Conflict",
                        "ErrorType": "IneligibleUpgrade",
                    }
                ],
            },
        },
        {
            "attributes": {
                "type": "PackagePushJob",
                "url": "/services/data/v43.0/sobjects/PackagePushJob/0DX1K000000LcxeWAC",
            },
            "Id": "0DX1K000000LcxeWAC",
            "SubscriberOrganizationKey": "00DJDITaMACaQZQ",
            "PackagePushErrors": {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "PackagePushError",
                            "url": "/services/data/v43.0/sobjects/PackagePushError/0DY1K00000013s8WAA",
                        },
                        "ErrorDetails": None,
                        "ErrorMessage": "This package requires that a newer version of a dependent package be installed before the upgrade can proceed: EDA, Version EDA 1.93.\n\nAsk the subscriber to install the dependent package and then retry the push upgrade.",
                        "ErrorSeverity": "Error",
                        "ErrorTitle": "Dependent Package Conflict",
                        "ErrorType": "IneligibleUpgrade",
                    }
                ],
            },
        },
        {
            "attributes": {
                "type": "PackagePushJob",
                "url": "/services/data/v43.0/sobjects/PackagePushJob/0DX1K000000LcvhWAC",
            },
            "Id": "0DX1K000000LcvhWAC",
            "SubscriberOrganizationKey": "00DUWEcFgynfLrd",
            "PackagePushErrors": {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "PackagePushError",
                            "url": "/services/data/v43.0/sobjects/PackagePushError/0DY1K00000013sNWAQ",
                        },
                        "ErrorDetails": None,
                        "ErrorMessage": "This package requires that a newer version of a dependent package be installed before the upgrade can proceed: EDA, Version EDA 1.93.\n\nAsk the subscriber to install the dependent package and then retry the push upgrade.",
                        "ErrorSeverity": "Error",
                        "ErrorTitle": "Dependent Package Conflict",
                        "ErrorType": "IneligibleUpgrade",
                    }
                ],
            },
        },
        {
            "attributes": {
                "type": "PackagePushJob",
                "url": "/services/data/v43.0/sobjects/PackagePushJob/0DX1K000000Lcy5WAC",
            },
            "Id": "0DX1K000000Lcy5WAC",
            "SubscriberOrganizationKey": "00DbbPwpmXbCdtC",
            "PackagePushErrors": {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "PackagePushError",
                            "url": "/services/data/v43.0/sobjects/PackagePushError/0DY1K00000013roWAA",
                        },
                        "ErrorDetails": None,
                        "ErrorMessage": "An unexpected failure was experienced during the upgrade. The subscriber's organization was unaffected. Contact salesforce.com Support through your normal channels and provide the following error number: 731858695-80805 (-151184096).",
                        "ErrorSeverity": "Error",
                        "ErrorTitle": "Unexpected Failure",
                        "ErrorType": "UnclassifiedError",
                    }
                ],
            },
        },
        {
            "attributes": {
                "type": "PackagePushJob",
                "url": "/services/data/v43.0/sobjects/PackagePushJob/0DX1K000000LctfWAC",
            },
            "Id": "0DX1K000000LctfWAC",
            "SubscriberOrganizationKey": "00DTGFxGeEIhFyj",
            "PackagePushErrors": {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "PackagePushError",
                            "url": "/services/data/v43.0/sobjects/PackagePushError/0DY1K00000013ryWAA",
                        },
                        "ErrorDetails": None,
                        "ErrorMessage": "This package requires that a newer version of a dependent package be installed before the upgrade can proceed: EDA, Version EDA 1.93.\n\nAsk the subscriber to install the dependent package and then retry the push upgrade.",
                        "ErrorSeverity": "Error",
                        "ErrorTitle": "Dependent Package Conflict",
                        "ErrorType": "IneligibleUpgrade",
                    }
                ],
            },
        },
        {
            "attributes": {
                "type": "PackagePushJob",
                "url": "/services/data/v43.0/sobjects/PackagePushJob/0DX1K000000LcvMWAS",
            },
            "Id": "0DX1K000000LcvMWAS",
            "SubscriberOrganizationKey": "00DmMBUTyLNccMM",
            "PackagePushErrors": {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "PackagePushError",
                            "url": "/services/data/v43.0/sobjects/PackagePushError/0DY1K00000013swWAA",
                        },
                        "ErrorDetails": None,
                        "ErrorMessage": "System.DmlException: Upsert failed. First exception on row 0 with id a4Ig00000001UZhEAM; first error: CANNOT_INSERT_UPDATE_ACTIVATE_ENTITY, hed.TDTM_TriggerHandler: execution of BeforeUpdate\n\ncaused by: System.UnexpectedException: common.exception.SfdcSqlException: ORA-04021: timeout occurred while waiting to lock object \n\n\nClass.gem.TDTM_Glue.getDefaultTdtmConfigTokens: line 66, column 1\nClass.gem.API_HEDA.getDefaultTdtmConfigTokens: line 50, column 1\nClass.hed.TDTM_Config.getTdtmConfig: line 67, column 1\nClass.hed.TDTM_Config.getClassesToCallForObject: line 134, column 1\nClass.hed.TDTM_TriggerHandler.run: line 68, column 1\nClass.hed.TDTM_Global_API.run: line 61, column 1\nTrigger.hed.TDTM_TriggerHandler: line 33, column 1: []\n\nClass.hed.TDTM_Manager.updateDefaultTdtmConfig: line 128, column 1\nClass.hed.TDTM_Global_API.setTdtmConfig: line 102, column 1\nClass.sfal.InstallScript.onInstall: line 5, column 1",
                        "ErrorSeverity": "Error",
                        "ErrorTitle": "Unexpected Error",
                        "ErrorType": "UnclassifiedError",
                    }
                ],
            },
        },
    ],
}


@pytest.fixture()
def push_failure_results():
    return PUSH_FAILURE_RESULT
