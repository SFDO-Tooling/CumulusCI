from cumulusci.tests.pytest_plugins.vcr_string_compressor import (
    StringToTemplateCompressor,
)

tpl_dir = "cumulusci/tests/shared_cassettes/vcr_string_templates"


example_string = """
<?xml version="1.0" encoding="UTF-8"?><jobInfo
   xmlns="http://www.force.com/2009/06/asyncapi/dataload">
 <id>75023000003RqO6AAK</id>
 <operation>insert</operation>
 <object>Account</object>
 <createdById>00523000002KbrQAAS</createdById>
 <createdDate>2022-03-29T20:03:56.000Z</createdDate>
 <systemModstamp>2022-03-29T20:03:56.000Z</systemModstamp>
 <state>Open</state>
 <concurrencyMode>Parallel</concurrencyMode>
 <contentType>CSV</contentType>
 <numberBatchesQueued>0</numberBatchesQueued>
 <numberBatchesInProgress>0</numberBatchesInProgress>
 <numberBatchesCompleted>0</numberBatchesCompleted>
 <numberBatchesFailed>0</numberBatchesFailed>
 <numberBatchesTotal>0</numberBatchesTotal>
 <numberRecordsProcessed>0</numberRecordsProcessed>
 <numberRetries>0</numberRetries>
 <apiVersion>vxx.0</apiVersion>
 <numberRecordsFailed>0</numberRecordsFailed>
 <totalProcessingTime>0</totalProcessingTime>
 <apiActiveProcessingTime>0</apiActiveProcessingTime>
 <apexProcessingTime>0</apexProcessingTime>
</jobInfo>""".strip()


class TestVcrStringToTemplateCompressor:
    def test_simple_string_compression(self):
        sc = StringToTemplateCompressor.from_directory(tpl_dir)
        data = sc.string_to_template_if_possible(example_string)
        assert data == {
            "include_template": "jobInfo_insert_xml.tpl",
            "vars": {
                "id": "75023000003RqO6AAK",
                "creator": "00523000002KbrQAAS",
                "cdate": "2022-03-29T20:03:56.000Z",
                "smts": "2022-03-29T20:03:56.000Z",
                "qdbatches": "0",
                "numbatchtotal": "0",
            },
        }
