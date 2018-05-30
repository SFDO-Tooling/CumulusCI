from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.tasks.salesforce import BaseRetrieveMetadata


retrieve_unpackaged_options = BaseRetrieveMetadata.task_options.copy()
retrieve_unpackaged_options.update({
    'package_xml': {
        'description': 'The path to a package.xml manifest to use for the retrieve.',
        'required': True,
    },
    'api_version': {
        'description': (
            'Override the default api version for the retrieve.' +
            ' Defaults to project__package__api_version'
        ),
    },
})

class RetrieveUnpackaged(BaseRetrieveMetadata):
    api_class = ApiRetrieveUnpackaged

    task_options = retrieve_unpackaged_options

    def _init_options(self, kwargs):
        super(RetrieveUnpackaged, self)._init_options(kwargs)

        if 'package_xml' in self.options:
            self.options['package_xml_path'] = self.options['package_xml']
            with open(self.options['package_xml_path'], 'r') as f:
                self.options['package_xml'] = f.read()

    def _get_api(self):
        return self.api_class(
            self,
            self.options['package_xml'],
            self.options.get('api_version'),
        )
