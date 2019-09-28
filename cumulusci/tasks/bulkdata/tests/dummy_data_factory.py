import factory
from cumulusci.tasks.bulkdata.factory_utils import ModuleDataFactory, Models


class GenerateDummyData(ModuleDataFactory):
    """Generate data based on test mapping.yml"""

    def make_records(self, num_records, factories):
        factories.create_batch("ContactFactory", num_records // 2)
        factories["ContactFactory"].create_batch(num_records // 4)
        factories.create_batch("AccountFactory", num_records // 4)


class AccountFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Models.accounts

    id = factory.Sequence(lambda i: i)
    Name = factory.Sequence(lambda i: "Account %d" % i)
    Street = "Baker St."


class ContactFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Models.contacts
        exclude = ["account"]  # don't try to attach the account to the Contact directly

    id = factory.Sequence(lambda n: n + 1)
    account = factory.SubFactory(AccountFactory)  # create account automatically
    account_id = factory.LazyAttribute(lambda o: o.account.id)
    firstname = factory.Faker("first_name")
    lastname = factory.Faker("last_name")
    email = factory.Faker("email", domain="salesforce.org")
    mailingstreet = "Baker St."
