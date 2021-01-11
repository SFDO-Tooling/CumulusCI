import pytest  # noqa: F401
from unittest import mock
from cumulusci.tests.util import create_project_config
from collections import defaultdict
from cumulusci.tasks.salesforce.tests.util import create_task

from cumulusci.tasks.salesforce.namespaces import (
    NamespaceInjectionMixin,
    namespace_injection_options,
)
from cumulusci.tasks.salesforce import BaseSalesforceMetadataApiTask


class NamespaceInjectionTask(BaseSalesforceMetadataApiTask, NamespaceInjectionMixin):
    task_options = {**namespace_injection_options}

    def _run_task(self):
        pass


class TestNamespaceInjectionMixin:
    def setup_method(self):
        self.namespace = "namespace_prefix"

        # NOTE: Most tests mock inject_namespace, so we are only asserting we pass in the arguments we expect.  There is not explicit use of these variables.  There are tests asserting we get the return values we expect from inject_namespace that use hard-coded values.
        self.filename = "___NAMESPACE__filename"
        self.content = "%%%NAMESPACE%%%CustomObject__c"

    def _create_task_in_managed_context(
        self, options: dict, project_namespace: str = None
    ) -> NamespaceInjectionTask:
        task = create_task(
            NamespaceInjectionTask,
            options,
            project_config=create_project_config(
                "TestRepo", "TestOwner", namespace=project_namespace
            ),
        )

        # Set OrgConfig.installed_packages so no callouts are performed.
        task.org_config._installed_packages = defaultdict(list)
        task.org_config._installed_packages[self.namespace].append(mock.Mock())

        return task

    def _create_task_in_namespaced_org_context(
        self, options: dict, project_namespace: str = None
    ) -> NamespaceInjectionTask:
        task = create_task(
            NamespaceInjectionTask,
            options,
            project_config=create_project_config(
                "TestRepo", "TestOwner", namespace=project_namespace
            ),
        )

        # Set OrgConfig.installed_packages so no callouts are performed.
        task.org_config._installed_packages = defaultdict(list)

        # Set OrgConfig as a namespaced org.
        task.org_config.config.update({"namespace": self.namespace})

        return task

    def _create_task_in_non_namespaced_org_context(
        self, options: dict, project_namespace: str = None
    ) -> NamespaceInjectionTask:
        task = create_task(
            NamespaceInjectionTask,
            options,
            project_config=create_project_config(
                "TestRepo", "TestOwner", namespace=project_namespace
            ),
        )

        # Set OrgConfig.installed_packages so no callouts are performed.
        task.org_config._installed_packages = defaultdict(list)

        return task

    @mock.patch("cumulusci.tasks.salesforce.namespaces.inject_namespace")
    def test_inject_namespace__defaults__managed_context(self, inject_namespace):
        task = self._create_task_in_managed_context(
            {}, project_namespace=self.namespace
        )

        actual = task._inject_namespace(self.filename, self.content)

        inject_namespace.assert_called_once_with(
            self.filename,
            self.content,
            namespace=self.namespace,
            managed=True,
            namespaced_org=False,
            logger=task.logger,
        )

        assert inject_namespace.return_value == actual

    @mock.patch("cumulusci.tasks.salesforce.namespaces.inject_namespace")
    def test_inject_namespace__defaults__managed_context__no_project_namespace(
        self, inject_namespace
    ):
        task = self._create_task_in_managed_context({}, project_namespace=None)

        actual = task._inject_namespace(self.filename, self.content)

        inject_namespace.assert_called_once_with(
            self.filename,
            self.content,
            namespace=None,
            managed=False,
            namespaced_org=False,
            logger=task.logger,
        )

        assert inject_namespace.return_value == actual

    @mock.patch("cumulusci.tasks.salesforce.namespaces.inject_namespace")
    def test_inject_namespace__defaults__namespaced_org_context(self, inject_namespace):
        task = self._create_task_in_namespaced_org_context(
            {}, project_namespace=self.namespace
        )

        actual = task._inject_namespace(self.filename, self.content)

        inject_namespace.assert_called_once_with(
            self.filename,
            self.content,
            namespace=self.namespace,
            managed=False,
            namespaced_org=True,
            logger=task.logger,
        )

        assert inject_namespace.return_value == actual

    @mock.patch("cumulusci.tasks.salesforce.namespaces.inject_namespace")
    def test_inject_namespace__defaults__namespaced_org_context__no_package_namespace(
        self, inject_namespace
    ):
        task = self._create_task_in_namespaced_org_context({}, project_namespace=None)

        actual = task._inject_namespace(self.filename, self.content)

        inject_namespace.assert_called_once_with(
            self.filename,
            self.content,
            namespace=None,
            managed=False,
            namespaced_org=False,
            logger=task.logger,
        )

        assert inject_namespace.return_value == actual

    @mock.patch("cumulusci.tasks.salesforce.namespaces.inject_namespace")
    def test_inject_namespace__defaults__non_namespaced_org_context(
        self, inject_namespace
    ):
        task = self._create_task_in_non_namespaced_org_context(
            {}, project_namespace=self.namespace
        )

        actual = task._inject_namespace(self.filename, self.content)

        inject_namespace.assert_called_once_with(
            self.filename,
            self.content,
            namespace=self.namespace,
            managed=False,
            namespaced_org=False,
            logger=task.logger,
        )

        assert inject_namespace.return_value == actual

    @mock.patch("cumulusci.tasks.salesforce.namespaces.inject_namespace")
    def test_inject_namespace__override_managed_option(self, inject_namespace):
        task = self._create_task_in_non_namespaced_org_context(
            {"managed": True}, project_namespace=self.namespace
        )

        actual = task._inject_namespace(self.filename, self.content)

        inject_namespace.assert_called_once_with(
            self.filename,
            self.content,
            namespace=self.namespace,
            managed=True,
            namespaced_org=False,
            logger=task.logger,
        )

        assert inject_namespace.return_value == actual

    @mock.patch("cumulusci.tasks.salesforce.namespaces.inject_namespace")
    def test_inject_namespace__override_namespaced_org_option(self, inject_namespace):
        task = self._create_task_in_non_namespaced_org_context(
            {"namespaced_org": True}, project_namespace=self.namespace
        )

        actual = task._inject_namespace(self.filename, self.content)

        inject_namespace.assert_called_once_with(
            self.filename,
            self.content,
            namespace=self.namespace,
            managed=False,
            namespaced_org=True,
            logger=task.logger,
        )

        assert inject_namespace.return_value == actual

    @mock.patch("cumulusci.tasks.salesforce.namespaces.inject_namespace")
    def test_inject_namespace__override_namespace_inject_option(self, inject_namespace):
        different_namespace = "different_namespace_prefix"
        task = self._create_task_in_non_namespaced_org_context(
            {"namespace_inject": different_namespace}, project_namespace=self.namespace
        )

        actual = task._inject_namespace(self.filename, self.content)

        inject_namespace.assert_called_once_with(
            self.filename,
            self.content,
            namespace=different_namespace,
            managed=False,
            namespaced_org=False,
            logger=task.logger,
        )

        assert inject_namespace.return_value == actual

    @mock.patch("cumulusci.tasks.salesforce.namespaces.inject_namespace")
    def test_inject_namespace__override_managed_arg(self, inject_namespace):
        task = self._create_task_in_non_namespaced_org_context(
            {}, project_namespace=self.namespace
        )

        actual = task._inject_namespace(self.filename, self.content, managed=True)

        inject_namespace.assert_called_once_with(
            self.filename,
            self.content,
            namespace=self.namespace,
            managed=True,
            namespaced_org=False,
            logger=task.logger,
        )

        assert inject_namespace.return_value == actual

    @mock.patch("cumulusci.tasks.salesforce.namespaces.inject_namespace")
    def test_inject_namespace__override_namespaced_org_arg(self, inject_namespace):
        task = self._create_task_in_non_namespaced_org_context(
            {}, project_namespace=self.namespace
        )

        actual = task._inject_namespace(
            self.filename, self.content, namespaced_org=True
        )

        inject_namespace.assert_called_once_with(
            self.filename,
            self.content,
            namespace=self.namespace,
            managed=False,
            namespaced_org=True,
            logger=task.logger,
        )

        assert inject_namespace.return_value == actual

    @mock.patch("cumulusci.tasks.salesforce.namespaces.inject_namespace")
    def test_inject_namespace__override_namespace_arg(self, inject_namespace):
        different_namespace = "different_namespace_prefix"
        task = self._create_task_in_non_namespaced_org_context(
            {}, project_namespace=self.namespace
        )

        actual = task._inject_namespace(
            self.filename, self.content, namespace=different_namespace
        )

        inject_namespace.assert_called_once_with(
            self.filename,
            self.content,
            namespace=different_namespace,
            managed=False,
            namespaced_org=False,
            logger=task.logger,
        )

        assert inject_namespace.return_value == actual

    def test_inject_namespace__return_values__namespace(self):
        task = self._create_task_in_non_namespaced_org_context(
            {}, project_namespace=self.namespace
        )

        filename, content = task._inject_namespace(
            "___NAMESPACE___CustomObject__c.object-meta.xml",
            "%%%NAMESPACE%%%CustomObject__c",
            managed=True,
            namespaced_org=False,
            namespace=self.namespace,
        )

        assert f"{self.namespace}__CustomObject__c.object-meta.xml" == filename
        assert f"{self.namespace}__CustomObject__c" == content

    def test_inject_namespace__return_values__namespace_dot(self):
        task = self._create_task_in_non_namespaced_org_context(
            {}, project_namespace=self.namespace
        )

        _, content = task._inject_namespace(
            "",
            "%%%NAMESPACE_DOT%%%ApexClass",
            managed=True,
            namespaced_org=False,
            namespace=self.namespace,
        )

        assert f"{self.namespace}.ApexClass" == content

    def test_inject_namespace__return_values__namespaced_org(self):
        task = self._create_task_in_non_namespaced_org_context(
            {}, project_namespace=self.namespace
        )

        filename, content = task._inject_namespace(
            "___NAMESPACED_ORG___CustomObject__c.object-meta.xml",
            "%%%NAMESPACED_ORG%%%CustomObject__c",
            managed=False,
            namespaced_org=True,
            namespace=self.namespace,
        )

        assert f"{self.namespace}__CustomObject__c.object-meta.xml" == filename
        assert f"{self.namespace}__CustomObject__c" == content

    def test_inject_namespace__return_values__namespace_or_c__namespace(self):
        task = self._create_task_in_non_namespaced_org_context(
            {}, project_namespace=self.namespace
        )

        _, content = task._inject_namespace(
            "",
            "%%%NAMESPACE_OR_C%%%-lwc",
            managed=True,
            namespaced_org=False,
            namespace=self.namespace,
        )

        assert f"{self.namespace}-lwc" == content

    def test_inject_namespace__return_values__namespaced_org_or_c__namespace(self):
        task = self._create_task_in_non_namespaced_org_context(
            {}, project_namespace=self.namespace
        )

        _, content = task._inject_namespace(
            "",
            "%%%NAMESPACED_ORG_OR_C%%%-lwc",
            managed=False,
            namespaced_org=True,
            namespace=self.namespace,
        )

        assert f"{self.namespace}-lwc" == content

    def test_get_namespaced_filename(self):
        task = self._create_task_in_non_namespaced_org_context(
            {}, project_namespace=self.namespace
        )
        namespace = mock.Mock()
        managed = mock.Mock()
        namespaced_org = mock.Mock()

        expected_filename = mock.Mock()
        expected_content = mock.Mock()

        task._inject_namespace = mock.Mock(
            return_value=(expected_filename, expected_content)
        )

        filename = task._get_namespaced_filename(
            "filename",
            namespace=namespace,
            managed=managed,
            namespaced_org=namespaced_org,
        )

        assert expected_filename == filename

        task._inject_namespace.assert_called_once_with(
            "filename",
            "",
            namespace=namespace,
            managed=managed,
            namespaced_org=namespaced_org,
        )

    def test_get_namespaced_content(self):
        task = self._create_task_in_non_namespaced_org_context(
            {}, project_namespace=self.namespace
        )
        namespace = mock.Mock()
        managed = mock.Mock()
        namespaced_org = mock.Mock()

        expected_filename = mock.Mock()
        expected_content = mock.Mock()

        task._inject_namespace = mock.Mock(
            return_value=(expected_filename, expected_content)
        )

        filename = task._get_namespaced_content(
            "content",
            namespace=namespace,
            managed=managed,
            namespaced_org=namespaced_org,
        )

        assert expected_content == filename

        task._inject_namespace.assert_called_once_with(
            "",
            "content",
            namespace=namespace,
            managed=managed,
            namespaced_org=namespaced_org,
        )
