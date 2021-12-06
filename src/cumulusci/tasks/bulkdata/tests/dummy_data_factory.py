import factory

from cumulusci.tasks.bulkdata.factory_utils import Models, ModuleDataFactory


class GenerateDummyData(ModuleDataFactory):
    """Generate data based on test mapping.yml"""

    def make_records(self, num_records, factories, current_batch_num):
        assert num_records % 4 == 0, "Use a batch size divisible by 4"
        factories.create_batch("ContactFactory", num_records // 2)
        factories["ContactFactory"].create_batch(num_records // 4)
        factories.create_batch("AccountFactory", num_records // 4)


class AccountFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Models.Account

    id = factory.Sequence(lambda i: i)
    Name = factory.Sequence(lambda i: "Account %d" % i)
    BillingStreet = "Baker St."


class ContactFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Models.Contact
        exclude = ["account"]  # don't try to attach the account to the Contact directly

    id = factory.Sequence(lambda n: n + 1)
    account = factory.SubFactory(AccountFactory)  # create account automatically
    AccountId = factory.LazyAttribute(lambda o: o.account.id)
    FirstName = factory.Faker("first_name")
    LastName = factory.Faker("last_name")
    Email = factory.Faker("email", domain="example.com")
    MailingStreet = "Baker St."
