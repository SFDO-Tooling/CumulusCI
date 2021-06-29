from unittest import mock

import pytest

from cumulusci.tasks.bulkdata.snowfakery import Snowfakery


@pytest.fixture
def snowfakery(request, create_task):
    def snowfakery(**kwargs):
        return create_task(Snowfakery, kwargs)

    return snowfakery


class TestSnowfakeryIntegration:
    def test_very_simple(self, snowfakery):
        task = snowfakery(recipe="datasets/recipe.yml")
        task()

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 3)
    def test_multipart_load(self, snowfakery):
        task = snowfakery(
            recipe="datasets/recipe.yml", run_until_records_loaded="Account:100"
        )
        task()
