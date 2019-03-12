from future.utils import bytes_to_native_str
import base64
import io
import os
import zipfile

from cumulusci.core.utils import process_bool_arg
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.tasks.salesforce import BaseSalesforceMetadataApiTask
from cumulusci.utils import cd
from cumulusci.utils import zip_clean_metaxml
from cumulusci.utils import zip_inject_namespace
from cumulusci.utils import zip_strip_namespace
from cumulusci.utils import zip_tokenize_namespace


class Deploy(BaseSalesforceMetadataApiTask):
    api_class = ApiDeploy
    task_options = {
        "path": {
            "description": "The path to the metadata source to be deployed",
            "required": True,
        },
        "unmanaged": {
            "description": "If True, changes namespace_inject to replace tokens with a blank string"
        },
        "namespace_inject": {
            "description": "If set, the namespace tokens in files and filenames are replaced with the namespace's prefix"
        },
        "namespace_strip": {
            "description": "If set, all namespace prefixes for the namespace specified are stripped from files and filenames"
        },
        "namespace_tokenize": {
            "description": "If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject"
        },
        "namespaced_org": {
            "description": "If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org."
        },
        "clean_meta_xml": {
            "description": "Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False"
        },
    }

    def _get_api(self, path=None):
        if not path:
            path = self.task_config.options__path

        package_zip = self._get_package_zip(path)
        self.logger.info("Payload size: {} bytes".format(len(package_zip)))
        return self.api_class(self, package_zip, purge_on_delete=False)

    def _include_directory(self, root_parts):
        # include the root directory, all non-lwc directories and sub-directories, and lwc component directories
        return len(root_parts) == 0 or root_parts[0] != "lwc" or len(root_parts) == 2

    def _include_file(self, root_parts, f):
        if len(root_parts) == 2 and root_parts[0] == "lwc":
            # is file of lwc component directory
            lower_f = f.lower()
            return lower_f.endswith((".js", ".js-meta.xml", ".html", ".css", ".svg"))
        return True

    def _get_files_to_package(self, path):
        for root, dirs, files in os.walk("."):
            root_parts = root.split(os.sep)[1:]
            if self._include_directory(root_parts):
                for f in files:
                    if self._include_file(root_parts, f):
                        yield os.path.join(root, f)

    def _get_package_zip(self, path):
        # Build the zip file
        zip_bytes = io.BytesIO()
        zipf = zipfile.ZipFile(zip_bytes, "w", zipfile.ZIP_DEFLATED)

        with cd(path):
            for file_to_package in self._get_files_to_package(path):
                zipf.write(file_to_package)
            zipf.close()

        zipf_processed = self._process_zip_file(zipfile.ZipFile(zip_bytes))
        fp = zipf_processed.fp
        zipf_processed.close()
        return bytes_to_native_str(base64.b64encode(fp.getvalue()))

    def _process_zip_file(self, zipf):
        zipf = self._process_namespace(zipf)
        zipf = self._process_meta_xml(zipf)
        return zipf

    def _process_namespace(self, zipf):
        if self.options.get("namespace_tokenize"):
            self.logger.info(
                "Tokenizing namespace prefix {}__".format(
                    self.options["namespace_tokenize"]
                )
            )
            zipf = zip_tokenize_namespace(
                zipf, self.options["namespace_tokenize"], logger=self.logger
            )
        if self.options.get("namespace_inject"):
            kwargs = {}
            kwargs["managed"] = not process_bool_arg(
                self.options.get("unmanaged", True)
            )
            kwargs["namespaced_org"] = process_bool_arg(
                self.options.get("namespaced_org", False)
            )
            kwargs["logger"] = self.logger
            if kwargs["managed"]:
                self.logger.info(
                    "Replacing namespace tokens from metadata with namespace prefix {}__".format(
                        self.options["namespace_inject"]
                    )
                )
            else:
                self.logger.info(
                    "Stripping namespace tokens from metadata for unmanaged deployment"
                )
            zipf = zip_inject_namespace(
                zipf, self.options["namespace_inject"], **kwargs
            )
        if self.options.get("namespace_strip"):
            zipf = zip_strip_namespace(
                zipf, self.options["namespace_strip"], logger=self.logger
            )
        return zipf

    def _process_meta_xml(self, zipf):
        if not process_bool_arg(self.options.get("clean_meta_xml", True)):
            return zipf

        self.logger.info(
            "Cleaning meta.xml files of packageVersion elements for deploy"
        )
        zipf = zip_clean_metaxml(zipf, logger=self.logger)
        return zipf
