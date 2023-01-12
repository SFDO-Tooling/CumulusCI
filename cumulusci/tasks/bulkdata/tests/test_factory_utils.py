import os

import factory
import pytest

from cumulusci.tasks.bulkdata import factory_utils
from cumulusci.tasks.bulkdata.tests.dummy_data_factory import (
    ContactFactory,
    GenerateDummyData,
)
from cumulusci.tasks.bulkdata.tests.utils import _make_task
from cumulusci.utils import temporary_dir


class TestFactoryUtils:
    def test_factory(self):
        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_vanilla_sf.yml")

        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "temp.db")
            dburl = "sqlite:///" + tmp_db_path
            task = _make_task(
                GenerateDummyData,
                {
                    "options": {
                        "num_records": 12,
                        "mapping": mapping_file,
                        "database_url": dburl,
                    }
                },
            )
            task()


class TestAdder:
    def test_adder(self):
        a = factory_utils.Adder(10)
        b = a(20)
        assert b == 30
        c = a(0)
        assert c == 30
        d = a(-5)
        assert d == 25
        a.reset(3)
        assert a(0) == 3


class TestFactories:
    def test_factories(self):
        class Broken(factory.alchemy.SQLAlchemyModelFactory):
            class Meta:
                model = "xyzzy"

        with pytest.raises(KeyError):
            factory_utils.Factories(None, {}, {"A": ContactFactory, "B": Broken})
