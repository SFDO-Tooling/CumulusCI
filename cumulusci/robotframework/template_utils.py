from jinja2 import Template


class StringGenerator:
    """ Sometimes in templates you want a reference to a variable to
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

    @property
    def faker(self):
        """Defer loading heavy faker library until actually needed"""
        self._faker = self._faker or __import__("faker").Faker()
        return self._faker

    def __getattr__(self, name):
        return StringGenerator(
            lambda *args, **kwargs: self.faker.format(name, *args, **kwargs)
        )


faker_template_library = FakerTemplateLibrary()


def format_str(value, i):
    if isinstance(value, str):
        value = Template(value).render(number=i, fake=faker_template_library)

    return value
