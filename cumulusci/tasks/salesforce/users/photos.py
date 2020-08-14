import re
import base64
import pathlib
import json

from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import CumulusCIException
from simple_salesforce.exceptions import SalesforceMalformedRequest


def join_errors(e: SalesforceMalformedRequest) -> str:
    return "; ".join([error.get("message", "Unknown.") for error in e.content])


class UploadProfilePhoto(BaseSalesforceApiTask):
    task_docs = """
Uploads a profile photo for a specified or default User.

Examples
--------

Upload a profile photo for the default user.

.. code-block:: yaml

    tasks:
        upload_profile_photo_default:
            group: Internal storytelling data
            class_path: cumulusci.tasks.salesforce.users.UploadProfilePhoto
            description: Uploads a profile photo for the default user.
            options:
                photo: storytelling/photos/default.png

Upload a profile photo for a user whose Alias equals ``grace`` or ``walker``, is active, and created today.

.. code-block:: yaml

    tasks:
        upload_profile_photo_grace:
            group: Internal storytelling data
            class_path: cumulusci.tasks.salesforce.users.UploadProfilePhoto
            description: Uploads a profile photo for Grace.
            options:
                photo: storytelling/photos/grace.png
                where: (Alias = 'grace' OR Alias = 'walker') AND IsActive = true AND CreatedDate = TODAY
    """

    task_options = {
        "photo": {"description": "Path to user's profile photo.", "required": True},
        "where": {
            "description": """WHERE clause used querying for which User to upload the profile photo for.

* No need to prefix with ``WHERE``

* The SOQL query must return one and only one User record.

* If no "where" is supplied, uploads the photo for the org's default User.

""",
            "required": False,
        },
    }

    def _raise_cumulusci_exception(self, e: SalesforceMalformedRequest) -> None:
        raise CumulusCIException(join_errors(e))

    def _get_user_id_by_query(self, where: str) -> str:
        # Query for the User removing a "WHERE " prefix from where if exists.
        query = "SELECT Id FROM User WHERE {} LIMIT 2".format(
            re.sub(r"^WHERE ", "", where, flags=re.I)
        )
        self.logger.info(f"Querying User: {query}")

        user_ids = []
        try:
            for record in self.sf.query_all(query)["records"]:
                user_ids.append(record["Id"])
        except SalesforceMalformedRequest as e:
            # Raise an easier to digest exception.
            self._raise_cumulusci_exception(e)

        # Validate only 1 User found.
        if len(user_ids) < 1:
            raise CumulusCIException("No Users found.")
        if 1 < len(user_ids):
            raise CumulusCIException(
                "More than one User found (at least 2): {}".format(", ".join(user_ids))
            )

        # Log and return User ID.
        self.logger.info(f"Uploading profile photo for the User with ID {user_ids[0]}")
        return user_ids[0]

    def _get_default_user_id(self) -> str:
        user_id = self.sf.restful("")["identity"][-18:]
        self.logger.info(
            f"Uploading profile photo for the default User with ID {user_id}"
        )
        return user_id

    def _insert_content_document(self, photo_path) -> str:
        path = pathlib.Path(photo_path)

        if not path.exists():
            raise CumulusCIException(f"No photo found at {path}")

        self.logger.info(f"Setting user photo to {path}")
        result = self.sf.ContentVersion.create(
            {
                "PathOnClient": path.name,
                "Title": path.stem,
                "VersionData": base64.b64encode(path.read_bytes()).decode("utf-8"),
            }
        )
        if not result["success"]:
            raise CumulusCIException(
                "Failed to create photo ContentVersion: {}".format(result["errors"])
            )
        content_version_id = result["id"]

        # Query the ContentDocumentId for our created record.
        content_document_id = self.sf.query(
            f"SELECT Id, ContentDocumentId FROM ContentVersion WHERE Id = '{content_version_id}'"
        )["records"][0]["ContentDocumentId"]

        self.logger.info(
            f"Uploaded profile photo ContentDocument {content_document_id}"
        )

        return content_document_id

    def _delete_content_document(self, content_document_id: str):
        self.sf.ContentDocument.delete(content_document_id)

    def _assign_user_profile_photo(self, user_id: str, content_document_id: str):
        # Call the Connect API to set our user photo.
        try:
            self.sf.restful(
                f"connect/user-profiles/{user_id}/photo",
                data=json.dumps({"fileId": content_document_id}),
                method="POST",
            )
        except SalesforceMalformedRequest as e:
            # Rollback ContentDocument, and raise an easier to digest exception.
            self.logger.error(
                "An error occured assigning the ContentDocument as the users's profile photo."
            )
            self.logger.error(f"Deleting ContentDocument {content_document_id}")
            self._delete_content_document(content_document_id)
            self._raise_cumulusci_exception(e)

    def _run_task(self):
        user_id = (
            self._get_user_id_by_query(self.options["where"])
            if self.options.get("where")
            else self._get_default_user_id()
        )

        content_document_id = self._insert_content_document(self.options["photo"])

        self._assign_user_profile_photo(user_id, content_document_id)
