import base64
import os
import json
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import CumulusCIException


class UploadDefaultUserProfilePhoto(BaseSalesforceApiTask):
    task_docs = """

    """

    task_options = {
        "photo_path": {
            "description": "Path to desired profile photo.",
            "required": True,
        }
    }

    def get_user_id(self):
        user_id = self.sf.restful("")["identity"][-18:]
        self.logger.info(
            f"Uploading profile photo for the default User with ID {user_id}."
        )
        return user_id

    def _run_task(self):
        # Get the User Id of the targeted user.
        user_id = self.get_user_id()

        # Upload profile photo ContentDocument.
        path = self.options["photo_path"]

        self.logger.info(f"Setting user photo to {path}")
        with open(path, "rb") as version_data:
            result = self.sf.ContentVersion.create(
                {
                    "PathOnClient": os.path.split(path)[-1],
                    "Title": os.path.splitext(os.path.split(path)[-1])[0],
                    "VersionData": base64.b64encode(version_data.read()).decode(
                        "utf-8"
                    ),
                }
            )
            if not result["success"]:
                raise CumulusCIException(
                    "Failed to create ContentVersion: {}".format(result["errors"])
                )
            content_version_id = result["id"]

        # Query the ContentDocumentId for our created record.
        content_document_id = self.sf.query(
            f"SELECT Id, ContentDocumentId FROM ContentVersion WHERE Id = '{content_version_id}'"
        )["records"][0]["ContentDocumentId"]

        self.logger.info(
            f"Uploaded profile photo ContentDocument {content_document_id}."
        )

        # Call the Connect API to set our user photo.
        result = self.sf.restful(
            f"connect/user-profiles/{user_id}/photo",
            data=json.dumps({"fileId": content_document_id}),
            method="POST",
        )


class UploadUserProfilePhoto(UploadDefaultUserProfilePhoto):
    task_docs = """
    Uploads a profile photo for a dynamically chosen User.  Specifically, uploads for a profile photo for the User whose ``user_field`` equals ``user_field_value``
    """

    task_options = {
        "user_field": {
            "description": 'User "string" Field to query against to find the User whom to upload the profile photo for.  "string" means the Field SOAP Type equals "xsd:string"',
            "required": True,
        },
        "user_field_value": {
            "description": "Value of the user_field that identifies the single User whom to upload the profile photo for.   An Exception is raised if no Users or more than 1 User is found whose user_field equals user_field_value.",
            "required": True,
        },
        **UploadDefaultUserProfilePhoto.task_options,
    }

    def validate_user_field(self, user_field):
        """
        Validates user_field:
        - is found
        - is filterable
        - is filterable with text
        """
        for field in self.sf.User.describe()["fields"]:
            if field["name"] == user_field:
                # Validate we can filter by user_field.
                if not field["filterable"]:
                    raise CumulusCIException(
                        f'user_field "{user_field}" must be filterable.'
                    )
                # Validate we can fulter by user_field with text.
                if field["soapType"] != "xsd:string":
                    raise CumulusCIException(
                        f'user_field "{user_field}" must be a text field.'
                    )

                return
        raise CumulusCIException(
            f'user_field "{user_field}" not found.  user_field must case-sensitive match a User Field name.'
        )

    def get_user_id(self):
        user_field = self.options["user_field"]
        user_field_value = self.options["user_field_value"]

        self.validate_user_field(user_field)

        result = self.sf.query(
            f"SELECT Id FROM User WHERE {user_field} = '{user_field_value}' LIMIT 2"
        )

        # Validate only 1 User found.
        if result["totalSize"] < 1:
            raise CumulusCIException(
                f"No Users found whose {user_field} equals '{user_field_value}'."
            )
        if 1 < result["totalSize"]:
            raise CumulusCIException(
                f"More than one User found whose {user_field} equals '{user_field_value}'."
            )

        user_id = result["records"][0]["Id"]
        self.logger.info(
            f"Uploading profile photo for User with ID {user_id} whose {user_field} equals '{user_field_value}'."
        )

        return user_id
