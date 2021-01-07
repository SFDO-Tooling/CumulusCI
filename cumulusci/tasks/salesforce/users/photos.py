import re
import json
from pathlib import Path
from cumulusci.tasks.salesforce import InsertContentDocument
from cumulusci.tasks.salesforce.content_documents import to_cumulusci_exception
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import CumulusCIException
from simple_salesforce.exceptions import SalesforceMalformedRequest


class UploadProfilePhoto(InsertContentDocument):
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

    def _init_options(self, kwargs):
        super(BaseSalesforceApiTask, self)._init_options(kwargs)

        self.options["path"] = Path(self.options.get("photo"))

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
            raise to_cumulusci_exception(e)

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

    def _get_record_ids_to_link(self) -> set[str]:
        self.logger.info("")
        record_ids = set()
        record_ids.add(
            self._get_user_id_by_query(self.options["where"])
            if self.options.get("where")
            else self._get_default_user_id()
        )
        return record_ids

    def _link_records_to_content_document(
        self, content_document_id: str, record_ids: set[str]
    ):
        # Call the Connect API to set our user photo.
        self.logger.info("")
        self.logger.info("Linking the Content Document as the User's Profile photo.")
        for user_id in record_ids:
            self.sf.restful(
                f"connect/user-profiles/{user_id}/photo",
                data=json.dumps({"fileId": content_document_id}),
                method="POST",
            )
