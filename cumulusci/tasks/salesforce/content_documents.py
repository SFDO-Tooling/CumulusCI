import base64
from pathlib import Path
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.core.exceptions import TaskOptionsError, CumulusCIException
from simple_salesforce.exceptions import SalesforceMalformedRequest
from cumulusci.utils import inject_namespace


def to_cumulusci_exception(e: SalesforceMalformedRequest) -> CumulusCIException:
    return CumulusCIException(
        "; ".join([error.get("message", "Unknown.") for error in e.content])
    )


class InsertContentDocument(BaseSalesforceApiTask):
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
        "path": {
            "description": "Path to the file to upload as a Content Document.",
            "required": True,
        },
        "queries": {
            "description": "List of SOQL queries whose records will be linked to the inserted Content Document.",
            "required": False,
        },
        "share_type": {
            "description": 'ContentDocumentLink.ShareType for all Content Document Links related to the new ContentDocument. Default: "I" (Inferred permission)',
            "required": False,
        },
        "visibility": {
            "description": 'ContentDocumentLink.Visibility for all Content Document Links related to the new ContentDocument. Default: "AllUsers"',
            "required": False,
        },
        "managed": {
            "description": "If False, changes namespace_inject to replace tokens with a blank string",
            "required": False,
        },
        "namespaced_org": {
            "description": "If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.",
            "required": False,
        },
        "namespace_inject": {
            "description": "If set, the namespace tokens in files and filenames are replaced with the namespace's prefix",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        path = Path(self.options.get("path"))

        if not path.exists() or not path.is_file():
            raise TaskOptionsError(
                f'Invalid "path". No file found at {self.options["path"]}'
            )

        # Process queries into a list + inject namespaces into queries.
        namespace = (
            self.options.get("namespace_inject")
            or self.project_config.project__package__namespace
        )
        if "managed" in self.options:
            managed = process_bool_arg(self.options["managed"])
        else:
            managed = (
                bool(namespace) and namespace in self.org_config.installed_packages
            )
        if "namespaced_org" in self.options:
            namespaced_org = process_bool_arg(self.options["namespaced_org"])
        else:
            namespaced_org = bool(namespace) and namespace == self.org_config.namespace

        queries = process_list_arg(self.options.get("queries") or [])
        for i, query in enumerate(queries):
            _, namespaced_query = inject_namespace(
                "",
                query,
                namespace=namespace,
                managed=managed,
                namespaced_org=namespaced_org,
            )
            queries[i] = namespaced_query
        self.options["queries"] = queries

        # Set defaults.
        self.options["share_type"] = self.options.get("share_type") or "I"

        self.options["visibility"] = self.options.get("visibility") or "AllUsers"

    def _insert_content_document(self) -> str:
        path = Path(self.options["path"])

        self.logger.info(f"Inserting ContentVersion from {path}")

        # Any failures raise a SalesforceMalformedRequest instead of returning success as False.
        result = self.sf.ContentVersion.create(
            {
                "PathOnClient": path.name,
                "Title": path.stem,
                "VersionData": base64.b64encode(path.read_bytes()).decode("utf-8"),
            }
        )
        content_version_id = result["id"]

        # Query the ContentDocumentId for our created record.
        content_document_id = self.sf.query(
            f"SELECT Id, ContentDocumentId FROM ContentVersion WHERE Id = '{content_version_id}'"
        )["records"][0]["ContentDocumentId"]

        self.logger.info(f'Success!  Inserted ContentDocument "{content_document_id}".')

        return content_document_id

    def _get_record_ids_to_link(self) -> list[str]:
        queries = self.options["queries"]
        self.logger.info("")
        self.logger.info("Querying records to link to the new ContentDocument.")
        all_record_ids = set()
        if queries:
            for query in queries:
                self.logger.info(f"    {query}")
                record_ids = [
                    record["Id"] for record in self.sf.query_all(query)["records"]
                ]
                if record_ids:
                    self.logger.info(
                        f"        ({len(record_ids)}) {', '.join(record_ids)}"
                    )
                    all_record_ids.update(record_ids)
                else:
                    self.logger.info("        🚫 No records found.")
        else:
            self.logger.info("    No queries specified.")
        return list(all_record_ids)

    def _link_records_to_content_document(
        self, content_document_id: str, record_ids: list[str]
    ):
        self.logger.info("")
        if record_ids:
            share_type = self.options["share_type"]
            visibility = self.options["visibility"]
            self.logger.info(
                "Inserting ContentDocumentLink records to link the ContentDocument."
            )
            self.logger.info(f'    ShareType: "{share_type}"')
            self.logger.info(f'    Visibility: "{visibility}"')
            for record_id in record_ids:
                self.sf.ContentDocumentLink.create(
                    {
                        "ContentDocumentId": content_document_id,
                        "LinkedEntityId": record_id,
                        "ShareType": share_type,
                        "Visibility": visibility,
                    }
                )
            self.logger.info(
                f'Successfully linked {len(record_ids)} record{"" if len(record_ids) == 1 else "s"} to Content Document "{content_document_id}"'
            )
        else:
            self.logger.info(
                "😴 No records IDs queried. Skipping linking the Content Document to related records."
            )

    def _run_task(self):
        # Insert the ContentDocument.
        content_document_id = self._insert_content_document()

        # Query records to link to the new ContentDocument.
        # "Rolls back" the ContentDocument insert if an Exception is raised.
        record_ids = None
        get_record_ids_to_link_exception = None
        try:
            record_ids = self._get_record_ids_to_link()
        except SalesforceMalformedRequest as e:
            # Convert SalesforceMalformedRequest into something easier to read
            get_record_ids_to_link_exception = to_cumulusci_exception(e)
        except Exception as e:
            get_record_ids_to_link_exception = e
        finally:
            if get_record_ids_to_link_exception:
                self.logger.error(
                    "An error occurred querying records to link to the ContentDocument."
                )
                # Reraise the Exception
                raise get_record_ids_to_link_exception

        # Links queried records to link to the new ContentDocument.
        # "Rolls back" the ContentDocument insert if an Exception is raised.
        link_records_to_content_document_exception = None
        try:
            self._link_records_to_content_document(content_document_id, record_ids)
        except SalesforceMalformedRequest as e:
            # Convert SalesforceMalformedRequest into something easier to read
            link_records_to_content_document_exception = to_cumulusci_exception(e)
        except Exception as e:
            link_records_to_content_document_exception = e
        finally:
            if link_records_to_content_document_exception:
                self.logger.error(
                    "An error occurred linking queried records to the ContentDocument."
                )
                # Reraise the Exception
                raise link_records_to_content_document_exception
