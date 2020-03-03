from cumulusci.utils.yaml.cumulusci_yml import parse_mapping_from_yaml


# fill this out.
class TestCumulusciYml:
    def test_cumulusci_yaml(self):
        parse_mapping_from_yaml("cumulusci.yml")
        parse_mapping_from_yaml("cumulusci/cumulusci.yml")
        parse_mapping_from_yaml("../NPSP/cumulusci.yml")
        parse_mapping_from_yaml("../Abacus/cumulusci.yml")
        parse_mapping_from_yaml("../CaseMan/cumulusci.yml")
