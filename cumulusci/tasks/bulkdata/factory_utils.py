from abc import ABCMeta, abstractmethod
from importlib import import_module

from factory import enums, base

from .base_generate_data_task import BaseGenerateDataTask


#  Factoryboy uses "__" and Salesforce uses "__". Luckily Factoryboy makes
#  theirs easy to override!
enums.SPLITTER = "____"


class Adder:
    """A more flexible alternative to Factoryboy sequences. You can create and
        destroy them wherever you want.

    >>> x = Adder(10)
    >>> x(1)
    11
    >>> x(1)
    12
    >>> x.reset(5)
    >>> x(2)
    7
    >>> x(2)
    9
    """

    def __init__(self, x=0):
        self.x = x

    def __call__(self, value):
        self.x += value
        return int(self.x)

    def reset(self, x):
        self.x = x


class Factories:
    """Thin collector for the factories and a place to experiment with
    techniques for better scalability than the create_batch function
    from FactoryBoy."""

    def __init__(self, session, orm_classes, collection):
        """Add a session to factories and then store them."""

        self.factory_classes = {
            key: self.add_session(value, session, orm_classes)
            for key, value in collection.items()
        }

    @staticmethod
    def add_session(fact, session, orm_classes):
        "Attach the session to the factory"
        fact._meta.sqlalchemy_session = session
        fact._meta.sqlalchemy_session_persistence = "flush"

        # if the model is just a string name, find a real class that matches
        # that name
        if isinstance(fact._meta.model, str):
            try:
                fact._meta.model = orm_classes[fact._meta.model]
            except KeyError:
                raise KeyError(
                    "ORM Class not found matching %s. Check mapping.yml"
                    % fact._meta.model
                )

        return fact

    def create_batch(self, classname, batchsize, **kwargs):
        cls = self.factory_classes.get(classname, None)
        assert cls, (
            "Cannot find a factory class named %s. Did you misspell it?" % classname
        )
        for _ in range(batchsize):
            cls.create(**kwargs)

    def __getitem__(self, name):
        return self.factory_classes[name]


class BaseDataFactory(BaseGenerateDataTask):
    """Abstract base class for any FactoryBoy based generator"""

    __metaclass__ = ABCMeta

    def generate_data(self, session, engine, base, num_records, current_batch_num):
        raw_factories = self.make_factories(base.classes)
        factories = Factories(session, base.classes, raw_factories)
        self.make_records(num_records, factories, current_batch_num)

    @abstractmethod
    def make_factories(self, classes):
        """Subclass to generate factory classes based on ORM classes."""

    @abstractmethod
    def make_records(self, num_records, factories, current_batch_num):
        """Subclass to make db records using factories."""


class ModuleDataFactory(BaseDataFactory):
    datafactory_classes_module = None
    # override to nominate a module to serve as the collection of modules

    def make_factories(self, classes):
        if not self.datafactory_classes_module:
            # by default look for classes in the same place that the derived class came from
            self.datafactory_classes_module = self.__module__
        module = import_module(self.datafactory_classes_module)
        module_contents = vars(module)

        # filter out other cruft from the file
        factories = {
            name: f
            for name, f in module_contents.items()
            if isinstance(f, base.FactoryMetaClass)
        }

        return factories


class _Models:
    """Stand in for the models module of a framework like Django"""

    def __getattr__(self, name):
        # Instead of returning model objects, return strings as stand-ins.
        # Later we'll replace the strings with real model objects after
        # doing the mapping.yml introspection.
        return name


Models = _Models()
