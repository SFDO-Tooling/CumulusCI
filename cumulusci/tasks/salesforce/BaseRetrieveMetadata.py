import os
import shutil
import zipfile
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.salesforce import BaseSalesforceMetadataApiTask
from cumulusci.utils import zip_inject_namespace
from cumulusci.utils import zip_strip_namespace
from cumulusci.utils import zip_tokenize_namespace


class BaseRetrieveMetadata(BaseSalesforceMetadataApiTask):
    task_options = {
        "path": {
            "description": "The path to write the retrieved metadata",
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
        "static_resource_path": {
            "description": "The path where decompressed static resources are stored.  Any retrieved StaticResource bundles will be unzipped into subdirectories under this path."
        },
    }

    def _run_task(self):
        api = self._get_api()
        src_zip = api()
        self._extract_zip(src_zip)
        self._decompress_static_resources()
        self.logger.info(
            "Extracted retrieved metadata into {}".format(self.options["path"])
        )

    def _process_namespace(self, src_zip):
        if self.options.get("namespace_tokenize"):
            src_zip = zip_tokenize_namespace(
                src_zip, self.options["namespace_tokenize"], logger=self.logger
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
            src_zip = zip_inject_namespace(
                src_zip, self.options["namespace_inject"], **kwargs
            )
        if self.options.get("namespace_strip"):
            src_zip = zip_strip_namespace(
                src_zip, self.options["namespace_strip"], logger=self.logger
            )
        return src_zip

    def _extract_zip(self, src_zip):
        src_zip = self._process_namespace(src_zip)
        src_zip.extractall(self.options["path"])

    def _decompress_static_resources(self):
        sr_path = self.options.get("static_resource_path")
        sr_src = os.path.join(self.options["path"], "staticresources")
        if sr_path and os.path.isdir(sr_src):
            if not os.path.isdir(sr_path):
                os.makedirs(sr_path)
            for filename in os.listdir(sr_src):
                file_path = os.path.join(sr_src, filename)
                if filename.endswith(".resource-meta.xml"):
                    os.rename(file_path, os.path.join(sr_path, filename))
                    continue
                if not filename.endswith(".resource"):
                    continue
                basename = filename.replace(".resource", "")
                self.logger.info("Decompressing {} static resource".format(basename))
                with open(file_path, "rb") as f:
                    zipf = zipfile.ZipFile(f)
                    zipf.extractall(os.path.join(sr_path, basename))
                os.remove(file_path)
            shutil.rmtree(sr_src)
