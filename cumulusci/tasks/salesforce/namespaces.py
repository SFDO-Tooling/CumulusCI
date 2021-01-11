from cumulusci.core.utils import process_bool_arg
from cumulusci.utils import inject_namespace
from typing import Optional, Tuple

namespace_injection_options = {
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


class NamespaceInjectionMixin:
    def _inject_namespace(
        self,
        filename: str,
        content: str,
        namespace: Optional[str] = None,
        managed: Optional[bool] = None,
        namespaced_org: Optional[bool] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        _namespace = (
            namespace
            or self.options.get("namespace_inject")
            or self.project_config.project__package__namespace
        )

        if managed is not None:
            _managed = managed
        elif "managed" in self.options:
            _managed = process_bool_arg(self.options["managed"])
        else:
            _managed = (
                bool(_namespace) and _namespace in self.org_config.installed_packages
            )

        if namespaced_org is not None:
            _namespaced_org = namespaced_org
        elif "namespaced_org" in self.options:
            _namespaced_org = process_bool_arg(self.options["namespaced_org"])
        else:
            _namespaced_org = (
                bool(_namespace) and _namespace == self.org_config.namespace
            )

        return inject_namespace(
            filename,
            content,
            namespace=_namespace,
            managed=_managed,
            namespaced_org=_namespaced_org,
            logger=self.logger,
        )

    def _get_namespaced_filename(
        self,
        filename,
        namespace: Optional[str] = None,
        managed: Optional[bool] = None,
        namespaced_org: Optional[bool] = None,
    ):
        filename, _ = self._inject_namespace(
            filename,
            "",
            namespace=namespace,
            managed=managed,
            namespaced_org=namespaced_org,
        )
        return filename

    def _get_namespaced_content(
        self,
        content,
        namespace: Optional[str] = None,
        managed: Optional[bool] = None,
        namespaced_org: Optional[bool] = None,
    ):
        _, content = self._inject_namespace(
            "",
            content,
            namespace=namespace,
            managed=managed,
            namespaced_org=namespaced_org,
        )
        return content
