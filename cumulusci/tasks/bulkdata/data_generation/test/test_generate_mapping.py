import unittest
from io import StringIO

import pytest

from cumulusci.tasks.bulkdata.data_generation.data_generator import generate
from cumulusci.tasks.bulkdata.data_generation.generate_mapping_from_factory import (
    mapping_from_factory_templates,
    build_dependencies,
    _table_is_free,
)
from cumulusci.tasks.bulkdata.data_generation.data_gen_exceptions import DataGenError
from cumulusci.tasks.bulkdata.data_generation.data_generator_runtime import Dependency


class TestGenerateMapping(unittest.TestCase):
    def test_simple_parent_child_reference(self):
        yaml = """
            - object: Parent
              fields:
                child:
                  - object: Child
              """
        summary = generate(StringIO(yaml), 1, {}, None)
        mapping = mapping_from_factory_templates(summary)
        assert len(mapping) == 2
        assert "Insert Parent" in mapping
        assert "Insert Child" in mapping
        assert mapping["Insert Parent"]["sf_object"] == "Parent"
        assert mapping["Insert Parent"]["table"] == "Parent"
        assert mapping["Insert Parent"]["fields"] == {}
        assert mapping["Insert Parent"]["lookups"]["child"]["table"] == "Child"
        assert mapping["Insert Parent"]["lookups"]["child"]["key_field"] == "child"

    def test_simple_child_parent_reference(self):
        yaml = """
            - object: Parent
              friends:
                  - object: Child
                    fields:
                      parent:
                        reference:
                          Parent
              """
        summary = generate(StringIO(yaml), 1, {}, None)
        mapping = mapping_from_factory_templates(summary)
        assert len(mapping) == 2
        assert "Insert Parent" in mapping
        assert "Insert Child" in mapping
        assert mapping["Insert Parent"]["sf_object"] == "Parent"
        assert mapping["Insert Parent"]["table"] == "Parent"
        assert mapping["Insert Parent"]["fields"] == {}
        assert mapping["Insert Child"]["lookups"]["parent"]["table"] == "Parent"

    def test_nickname_reference(self):
        yaml = """
            - object: Target
              nickname: bubba
            - object: Referrer
              fields:
                food: shrimp
                shrimpguy:
                  reference:
                    bubba
              """
        summary = generate(StringIO(yaml), 1, {}, None)
        mapping = mapping_from_factory_templates(summary)
        assert len(mapping) == 2
        assert "Insert Target" in mapping
        assert "Insert Referrer" in mapping
        assert mapping["Insert Target"]["sf_object"] == "Target"
        assert mapping["Insert Referrer"]["table"] == "Referrer"
        assert mapping["Insert Referrer"]["fields"] == {"food": "food"}
        assert mapping["Insert Referrer"]["lookups"]["shrimpguy"]["table"] == "Target"

    def test_forward_reference(self):
        yaml = """
            - object: A
              nickname: alpha
              fields:
                B:
                  reference:
                    bubba
            - object: B
              nickname: bubba
              fields:
                A:
                  reference:
                    alpha
              """
        with self.assertRaises(DataGenError):
            generate(StringIO(yaml), 1, {}, None)

    def test_circular_table_reference(self):
        yaml = """
            - object: A
              fields:
                B:
                  - object: B
            - object: B
              fields:
                A:
                  - object: A
              """
        summary = generate(StringIO(yaml), 1, {}, None)
        with pytest.warns(UserWarning, match="Circular"):
            mapping_from_factory_templates(summary)

    def test_cats_and_dogs(self):
        yaml = """
            - object: PetFood
              nickname: DogFood
            - object: PetFood
              nickname: CatFood
            - object: Person
              fields:
                dog:
                    - object: Animal
                      fields:
                            food:
                                reference: DogFood
                cat:
                    - object: Animal
                      fields:
                            food:
                                reference: CatFood
"""
        summary = generate(StringIO(yaml), 1, {}, None)
        mapping = mapping_from_factory_templates(summary)
        assert len(mapping) == 3
        assert "Insert Person" in mapping
        assert "Insert PetFood" in mapping
        assert "Insert Animal" in mapping
        assert mapping["Insert Person"]["sf_object"] == "Person"
        assert mapping["Insert Person"]["table"] == "Person"
        assert mapping["Insert Person"]["fields"] == {}
        assert mapping["Insert Person"]["lookups"]["dog"]["table"] == "Animal"
        assert mapping["Insert Person"]["lookups"]["dog"]["key_field"] == "dog"
        assert mapping["Insert Person"]["lookups"]["cat"]["table"] == "Animal"
        assert mapping["Insert Person"]["lookups"]["cat"]["key_field"] == "cat"
        assert mapping["Insert PetFood"]["sf_object"] == "PetFood"
        assert mapping["Insert PetFood"]["table"] == "PetFood"
        assert mapping["Insert PetFood"]["fields"] == {}
        assert mapping["Insert PetFood"]["lookups"] == {}
        assert mapping["Insert Animal"]["sf_object"] == "Animal"
        assert mapping["Insert Animal"]["table"] == "Animal"
        assert mapping["Insert Animal"]["fields"] == {}
        assert mapping["Insert Animal"]["lookups"]["food"]["table"] == "PetFood"
        assert mapping["Insert Animal"]["lookups"]["food"]["key_field"] == "food"


class TestBuildDependencies(unittest.TestCase):
    def test_build_dependencies_simple(self):
        parent_deps = [
            Dependency("parent", "child", "son"),
            Dependency("parent", "child", "daughter"),
        ]
        child_deps = [
            Dependency("child", "grandchild", "son"),
            Dependency("child", "grandchild", "daughter"),
        ]
        deps = parent_deps + child_deps
        dependencies, reference_fields = build_dependencies(deps)
        assert dependencies == {"parent": set(parent_deps), "child": set(child_deps)}
        assert reference_fields == {
            ("parent", "daughter"): "child",
            ("parent", "son"): "child",
            ("child", "daughter"): "grandchild",
            ("child", "son"): "grandchild",
        }

        # test repr
        [repr(o) for o in deps]


class TestTableIsFree(unittest.TestCase):
    def test_table_is_free_simple(self):
        # Child depends on parent and parent hasn't been sorted out yet -> false
        assert not _table_is_free(
            "Child", {"Child": {Dependency("Child", "Parent", "parent")}}, []
        )

        # Child depends on parent and parent has been sorted out already -> ]true
        assert _table_is_free(
            "Child", {"Child": {Dependency("Child", "Parent", "parent")}}, ["Parent"]
        )

        # Child depends on parent and parent hasn't been sorted out yet. -> false
        assert not _table_is_free(
            "Child",
            {
                "Child": {
                    Dependency("Child", "Parent", "parent"),
                    Dependency("Parent", "Grandparent", "parent"),
                }
            },
            ["Grandparent"],
        )

        # Child depends on parent and parent has been sorted out already -> true
        assert _table_is_free(
            "Child",
            {
                "Child": {
                    Dependency("Child", "Parent", "parent"),
                    Dependency("Parent", "Grandparent", "parent"),
                }
            },
            ["Grandparent", "Parent"],
        )
