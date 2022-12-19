from typing import Mapping, Sequence

import sqlalchemy.types as types
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm.collections import attribute_mapped_collection

Base = declarative_base()


class SpecializedType(types.TypeDecorator):
    """A baseclass for custom datatypes. E.g. sequences and mappings

    Custom types are types that are not directly supported by SQL Alchemy
    """

    impl = types.PickleType

    def process_bind_param(self, value, dialect):
        assert isinstance(value, (self.typ, type(None))), (value, self.typ)
        if not value:
            return None
        return self.empty_value.__class__(value)

    def process_result_value(self, value, dialect):
        if not value:
            return self.empty_value
        return value

    def copy(self, **kw):
        return self.__class__(self.impl.length)


class SequenceType(SpecializedType):
    """Store sequences in an optimized tuple format"""

    typ = Sequence
    empty_value = ()


class MappingType(SpecializedType):
    """Store mappings in an optimized dict format"""

    typ = Mapping
    empty_value = {}


class OrgSchemaModelMixin:
    def __getitem__(self, attr):
        try:
            return getattr(self, attr)
        except AttributeError:
            raise KeyError(attr)

    def __repr__(self):
        fields = self.__dict__.copy()
        name = fields.pop("name", "<UNNAMED>")
        fields.pop("_sa_instance_state")
        return f"<{self.__class__.__name__} {name} {fields}>"

    def __eq__(self, other):
        "Useful mostly for unit tests"
        my_state = self.__dict__.copy()
        my_state.pop("_sa_instance_state")
        other_state = other.__dict__.copy()
        other_state.pop("_sa_instance_state", None)
        return my_state == other_state


class SObject(OrgSchemaModelMixin, Base):
    __tablename__ = "sobjects"
    name = Column(String, primary_key=True, sqlite_on_conflict_primary_key="REPLACE")
    activateable = Column(Boolean)
    childRelationships = Column(SequenceType)
    compactLayoutable = Column(Boolean)
    createable = Column(Boolean)
    custom = Column(Boolean)
    customSetting = Column(Boolean)
    deepCloneable = Column(Boolean)
    defaultImplementation = Column(String)
    deletable = Column(Boolean)
    deprecatedAndHidden = Column(Boolean)
    extendedBy = Column(String)
    extendsInterfaces = Column(String)
    feedEnabled = Column(Boolean)
    fields = relationship(
        "Field",
        collection_class=attribute_mapped_collection("name"),
        back_populates="parent",
    )
    hasSubtypes = Column(Boolean)
    label = Column(String)
    labelPlural = Column(String)
    implementedBy = Column(String)
    implementsInterfaces = Column(String)
    isInterface = Column(Boolean)
    isSubtype = Column(Boolean)
    keyPrefix = Column(String)
    layoutable = Column(Boolean)
    listviewable = Column(String)
    lookupLayoutable = Column(String)
    mergeable = Column(Boolean)
    mruEnabled = Column(Boolean)
    namedLayoutInfos = Column(SequenceType)
    networkScopeFieldName = Column(String)
    queryable = Column(Boolean)
    recordTypeInfos = Column(SequenceType)
    replicateable = Column(Boolean)
    retrieveable = Column(Boolean)
    searchLayoutable = Column(Boolean)
    searchable = Column(Boolean)
    sobjectDescribeOption = Column(String)
    triggerable = Column(Boolean)
    undeletable = Column(Boolean)
    updateable = Column(Boolean)
    urls = Column(MappingType)
    supportedScopes = Column(SequenceType)
    actionOverrides = Column(SequenceType)
    count = Column(Integer)
    last_modified_date = Column(String)

    @property
    def extractable(self):
        return self.createable and self.queryable and self.retrieveable


field_references = Table(
    "references",
    Base.metadata,
    Column("field_name", Integer, ForeignKey("fields.name")),
    Column("object_name", Integer, ForeignKey("sobjects.name")),
)


class Field(OrgSchemaModelMixin, Base):
    __tablename__ = "fields"
    __table_args__ = (
        PrimaryKeyConstraint(
            "sobject", "name", name="foo", sqlite_on_conflict="REPLACE"
        ),
    )

    sobject = Column(String, ForeignKey("sobjects.name"), nullable=False)
    parent = relationship("SObject", back_populates="fields")
    name = Column(String, nullable=False)
    aggregatable = Column(Boolean)
    aiPredictionField = Column(Boolean)
    autoNumber = Column(Boolean)
    byteLength = Column(Integer)
    calculated = Column(Boolean)
    calculatedFormula = Column(String)
    cascadeDelete = Column(Boolean)
    caseSensitive = Column(Boolean)
    compoundFieldName = Column(String)
    controllerName = Column(String)
    createable = Column(Boolean)
    custom = Column(Boolean)
    defaultValue = Column(String)
    defaultValueFormula = Column(String)
    defaultedOnCreate = Column(Boolean)
    dependentPicklist = Column(Boolean)
    deprecatedAndHidden = Column(Boolean)
    digits = Column(Integer)
    displayLocationInDecimal = Column(Boolean)
    encrypted = Column(Boolean)
    externalId = Column(Boolean)
    extraTypeInfo = Column(types.PickleType)
    filterable = Column(Boolean)
    filteredLookupInfo = Column(types.PickleType)
    formulaTreatNullNumberAsZero = Column(Boolean)
    groupable = Column(Boolean)
    highScaleNumber = Column(Boolean)
    htmlFormatted = Column(Boolean)
    idLookup = Column(Boolean)
    inlineHelpText = Column(String)
    label = Column(String)
    length = Column(Integer)
    mask = Column(String)
    maskType = Column(String)
    name = Column(String)
    nameField = Column(Boolean)
    namePointing = Column(Boolean)
    nillable = Column(Boolean)
    permissionable = Column(Boolean)
    polymorphicForeignKey = Column(Boolean)
    precision = Column(Integer)
    queryByDistance = Column(Boolean)
    referenceTargetField = Column(String)
    referenceTo = Column(types.PickleType)
    relationshipName = Column(String)
    relationshipOrder = Column(Integer)
    restrictedDelete = Column(Boolean)
    restrictedPicklist = Column(Boolean)
    scale = Column(Integer)
    searchPrefilterable = Column(Boolean)
    soapType = Column(String)
    sortable = Column(Boolean)
    type = Column(String)
    unique = Column(Boolean)
    updateable = Column(Boolean)
    writeRequiresMasterRead = Column(Boolean)
    picklistValues = Column(types.PickleType)

    @property
    def requiredOnCreate(self):
        defaulted = (
            self.defaultValue is not None  # has a real default value
            or self.nillable  # None is a valid default value
            or self.defaultedOnCreate  # defaulted some other way
        )
        return self.createable and not defaulted


class FileMetadata(Base):
    __tablename__ = "file_metadata"
    name = Column(String, primary_key=True, sqlite_on_conflict_primary_key="REPLACE")
    value = Column(String)
