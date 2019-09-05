import factory
from cumulusci.tasks.bulkdata.factory_utils import ModuleDataFactory, Models


class GenerateDummyData(ModuleDataFactory):
    """Generate data based on test mapping.yml"""

    def make_records(self, num_records, factories):
        factories.create_batch("Contact", 10)
        factories["Contact"].create_batch(5)
        factories.create_batch("Household", 5)


class Household(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Models.households

    name = factory.sequence(lambda i: "Household %d" % i)


class Contact(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Models.contacts
        exclude = [
            "household"
        ]  # don't try to attach the household to the Contact directly

    id = factory.Sequence(lambda n: n + 1)
    household = factory.SubFactory(Household)  # create households automatically
    first_name = factory.sequence(lambda i: "Gordon %d" % i)
    last_name = factory.sequence(lambda i: "Everyman %d" % i)
    email = factory.sequence(lambda i: "gevm%d@example.com" % i)
    household_id = factory.LazyAttribute(lambda o: o.household.id)
