import faker
from robot.libraries.BuiltIn import RobotNotRunningError


class FakerMixin:
    """Mixin class which provides support for the faker library"""

    def __init__(self):
        super().__init__()
        self._faker = faker.Faker("en_US")
        try:
            self.builtin.set_global_variable("${faker}", self._faker)
        except RobotNotRunningError:
            # this only happens during unit tests, and we don't care.
            pass

    def set_faker_locale(self, locale):
        """Set the locale for fake data

        This sets the locale for all calls to the ``Faker`` keyword
        and ``${faker}`` variable. The default is en_US

        For a list of supported locales see
        [https://faker.readthedocs.io/en/master/locales.html|Localized Providers]
        in the Faker documentation.

        Example

        | Set Faker Locale    fr_FR
        | ${french_address}=  Faker  address

        """
        try:
            self._faker = faker.Faker(locale)
        except AttributeError:
            raise Exception(f"Unknown locale for fake data: '{locale}'")

    def get_fake_data(self, fake, *args, **kwargs):
        """Return fake data

        This uses the [https://faker.readthedocs.io/en/master/|Faker]
        library to provide fake data in a variety of formats (names,
        addresses, credit card numbers, dates, phone numbers, etc) and
        locales (en_US, fr_FR, etc).

        The _fake_ argument is the name of a faker property such as
        ``first_name``, ``address``, ``lorem``, etc. Additional
        arguments depend on type of data requested. For a
        comprehensive list of the types of fake data that can be
        generated see
        [https://faker.readthedocs.io/en/master/providers.html|Faker
        providers] in the Faker documentation.

        The return value is typically a string, though in some cases
        some other type of object will be returned. For example, the
        ``date_between`` fake returns a
        [https://docs.python.org/3/library/datetime.html#date-objects|datetime.date
        object]. Each time a piece of fake data is requested it will
        be regenerated, so that multiple calls will usually return
        different data.

        This keyword can also be called using robot's extended variable
        syntax using the variable ``${faker}``. In such a case, the
        data being asked for is a method call and arguments must be
        enclosed in parentheses and be quoted. Arguments should not be
        quoted when using the keyword.

        To generate fake data for a locale other than en_US, use
        the keyword ``Set Faker Locale`` prior to calling this keyword.

        Examples

        | # Generate a fake first name
        | ${first_name}=  Get fake data  first_name

        | # Generate a fake date in the default format
        | ${date}=  Get fake data  date

        | # Generate a fake date with an explicit format
        | ${date}=  Get fake data  date  pattern=%Y-%m-%d

        | # Generate a fake date using extended variable syntax
        | Input text  //input  ${faker.date(pattern='%Y-%m-%d')}

        """
        try:
            return self._faker.format(fake, *args, **kwargs)
        except AttributeError:
            raise Exception(f"Unknown fake data request: '{fake}'")
