from re import compile
import time

from cumulusci.utils.iterators import iterate_in_chunks

COUNT_BREAKPOINT = 1_000_000

start = time.time()
exclusions = [
    "AlternativePaymentMethod.*",
    "Shift.*",
    "ContentDocumentLink",
    "ContentDistribution",
    "PaymentAuthAdjustment",
    "Vote",
    "ProductServiceCampaignItem",
    "ShipmentItem",
    "IdeaComment",
    "FinanceTransaction",
    "WorkOrder.*",
    "Prompt.*",
    "ReturnOrder.*",
    "User.*",
    "npsp__Schedulable__c",
    ".*Trigger_Handler__c",
    ".*Settings.*",
    "npsp__Level__c",
    ".*Error.*",
    "npsp__Batch__c",
    "npsp__Relationship_Sync_Excluded_Fields__c",
    ".*DataImport__c",
    "NetworkUserHistoryRecent",
    ".*Permission.*",
    "SetupEntityAccess",
    "PricebookEntry",
    "Group",
    "WorkBadge.*",
    "WorkAccess",
    "EmailTemplate",
    "WebLink",
    "RecordType",
    ".*Share",
    ".*Template.*",
]
exclusions = [compile(e) for e in exclusions]
bad_objects = set()
bad_fields = []
errors = []
weird_fields = [
    ("CalendarView", "PublisherId"),
    ("ContractLineItem", "LocationId"),
    ("FieldServiceMobileSettings", "QuickStatusChangeFlowName"),
    ("GtwyProvPaymentMethodType", "RecordTypeId"),
    ("Entitlement", "RemainingWorkOrders"),
    ("Entitlement", "WorkOrdersPerEntitlement"),
    ("Expense", "Discount"),
    ("Expense", "Quantity"),
    ("Expense", "UnitPrice"),
    ("MaintenanceWorkRule", "ParentMaintenancePlanId"),
    ("ProductConsumed", "Discount"),
    ("OrgWideEmailAddress", "Purpose"),
]


def get_record_counts(sf):
    record_counts = sf.restful("limits/recordCount")["sObjects"]

    return {record["name"]: record["count"] for record in record_counts}


def find_populated_fields_small_sobject(sf, sobject):
    local_field_counts = {}
    fields = (
        f
        for f in sobject.fields.values()
        if f.createable
        and f.aggregatable
        and (sobject.name, f.name) not in weird_fields
    )

    # query for N fields at a time
    for idx, fieldset in enumerate(iterate_in_chunks(100, fields)):
        field_names = sorted(field.name for field in fieldset)
        field_list = ",".join(
            f"count({fieldname}) num_{fieldname}" for fieldname in field_names
        )
        try:
            query = f"select {field_list} from {sobject.name}"
            result = sf.query(query)
            assert len(result["records"]) == 1
            counts = result["records"][0]
            del counts["attributes"]
            local_field_counts.update(
                {(sobject.name, k[4:]): v for k, v in counts.items()}
            )

        except Exception as e:
            if "INVALID_TYPE" in str(e):
                print(e)
                bad_objects.add(sobject.name)
            elif "Implementation restriction. When querying the" in str(
                e
            ) and "Implementation restriction. When querying" in str(e):
                print(e)
                bad_objects.add(sobject.name)
            else:
                raise
                # print(sobject.name, field.name, e, field)
                # errors.append((sobject.name, field.name))
    return local_field_counts


def find_populated_fields_large_sobject(sf, sobject):
    print("Using rough heuristic for", sobject.name, "due to large record count.")
    return {(sobject.name, field): COUNT_BREAKPOINT for field in sobject.fields}


def find_populated_fields(org_config, sobject_list):
    sf = org_config.salesforce_client
    record_counts = get_record_counts(sf)
    field_count = {}
    with org_config.get_org_schema() as schema:
        print(time.time() - start)
        for sobject in sorted(schema.sobjects, key=lambda x: x.name):
            if (
                not sobject.queryable
                or not sobject.retrieveable
                or sobject.deprecatedAndHidden
            ) and sobject.name in sobject_list:
                print("Skipping", sobject.name, "due to properties")
                continue
            if any(exclusion.fullmatch(sobject.name) for exclusion in exclusions):
                print("Skipping", sobject.name, "due to exclusion list")
                continue

            print(sobject.name)
            if record_counts.get(sobject.name, 0) < COUNT_BREAKPOINT:
                local_field_counts = find_populated_fields_small_sobject(sf, sobject)
            else:
                local_field_counts = find_populated_fields_large_sobject(sf, sobject)

            field_count.update(local_field_counts)

    return field_count


def populated_fields(org_config):
    with org_config.get_org_schema() as schema:
        sobject_list = (s.name for s in schema.sobjects)
        field_counts = find_populated_fields(org_config, sobject_list)
        return sorted((f for f in field_counts.items() if f[-1]), key=lambda x: x[-1])


if __name__ == "__main__":
    from cumulusci.cli.runtime import CliRuntime
    from sys import argv

    runtime = CliRuntime(load_keychain=True)

    if len(argv) > 1:
        orgname = argv[1]
    else:
        orgname = "qa"

    name, org_config = runtime.get_org(orgname)

    fields = populated_fields(org_config)

    sobjs = {}
    for (sobjname, fieldname), count in fields:
        sobjs.setdefault(sobjname, []).append(fieldname)
