from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.orm.collections import attribute_mapped_collection
import sqlalchemy.types as types
from sqlalchemy import PrimaryKeyConstraint

Base = declarative_base()


class OrgSchemaModelMixin:
    def __getitem__(self, attr):
        try:
            return getattr(self, attr)
        except AttributeError:
            raise KeyError(attr)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name}>"


class SObject(OrgSchemaModelMixin, Base):
    __tablename__ = "sobjects"
    # id = Column(Integer, primary_key=True)
    name = Column(String, primary_key=True, sqlite_on_conflict_primary_key="REPLACE")
    activateable = Column(Boolean)
    childRelationships = Column(types.PickleType)
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
        "Field", collection_class=attribute_mapped_collection("name"),
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
    namedLayoutInfos = Column(types.PickleType)
    networkScopeFieldName = Column(String)
    queryable = Column(Boolean)
    recordTypeInfos = Column(types.PickleType)
    replicateable = Column(Boolean)
    retrieveable = Column(Boolean)
    searchLayoutable = Column(Boolean)
    searchable = Column(Boolean)
    sobjectDescribeOption = Column(String)
    triggerable = Column(Boolean)
    undeletable = Column(Boolean)
    updateable = Column(Boolean)
    urls = Column(types.PickleType)
    supportedScopes = Column(types.PickleType)
    actionOverrides = Column(types.PickleType)


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

    # id = Column(Integer, primary_key=True)
    sobject = Column(String, ForeignKey("sobjects.name"), nullable=False)
    parent = relationship("SObject")
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


class FileMetadata(Base):
    __tablename__ = "file_metadata"
    name = Column(String, primary_key=True, sqlite_on_conflict_primary_key="REPLACE")
    value = Column(String)
