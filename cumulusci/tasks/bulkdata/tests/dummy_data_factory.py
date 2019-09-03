from datetime import date, datetime

import factory
from cumulusci.tasks.bulkdata.factory_utils import ModuleDataFactory, Models


def now():
    return datetime.now().date()


START_DATE = date(2019, 1, 1)  # Per https://salesforce.quip.com/gLfGAPtqVzUS


class GenerateDummyData(ModuleDataFactory):
    """Generate data specific to a particular use case"""

    def make_records(self, num_records, factories):
        factories.create_batch("Contact", 10)
        factories.create_batch("Household", 5)


class Household(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Models.households

    name = factory.sequence(lambda i: f"Household {i}")


class Contact(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Models.contacts
        exclude = [
            "household"
        ]  # don't try to attach the household to the Contact directly

    id = factory.Sequence(lambda n: n + 1)
    household = factory.SubFactory(Household)  # create households automatically
    first_name = factory.sequence(lambda i: f"Gordon {i}")
    last_name = factory.sequence(lambda i: f"Everyman {i}")
    email = factory.sequence(lambda i: f"gevm{i}@example.com")
    household_id = factory.LazyAttribute(lambda o: o.household.id)
