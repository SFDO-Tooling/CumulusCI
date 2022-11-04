from functools import lru_cache

from faker import Faker
from jinja2 import Template


class StringGenerator:
    """Sometimes in templates you want a reference to a variable to
    call a function.

    For example:

    >>> x = template_utils.StringGenerator(datetime.today().isoformat)
    >>> print(f"{x}")
    2019-09-23T11:49:01.994453

    >>> x = template_utils.StringGenerator(lambda:str(random.random()))
    >>> print(f"{x}")
    0.795273959965055
    >>> print(f"{x}")
    0.053061903749985206
    """

    def __init__(self, func):
        self.func = func

    def __str__(self):
        return self.func()

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class FakerTemplateLibrary:
    """A Jinja template library to add the faker.xyz objects to templates"""

    _faker = None

    def __init__(self, locale=None):
        self.locale = locale
        self.faker = Faker(self.locale)

    def __getattr__(self, name):
        return StringGenerator(
            lambda *args, **kwargs: self.faker.format(name, *args, **kwargs)
        )


faker_template_library = FakerTemplateLibrary()

Template = lru_cache(512)(Template)


def format_str(value, variables=None, fake=faker_template_library):
    variables = variables or {}
    if isinstance(value, str) and "{" in value:
        value = Template(value).render(fake=fake, **variables)

    return value
