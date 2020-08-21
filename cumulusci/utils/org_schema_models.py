from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.orm.collections import attribute_mapped_collection
import sqlalchemy.types as types

Base = declarative_base()


class SObject(Base):
    __tablename__ = "sobjects"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
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

    def __repr__(self):
        return f"<{self.name} at {self.id}>"


field_references = Table(
    "references",
    Base.metadata,
    Column("field_id", Integer, ForeignKey("fields.id")),
    Column("object_id", Integer, ForeignKey("sobjects.id")),
)


class Field(Base):
    __tablename__ = "fields"
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("sobjects.id"), nullable=False)
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
    extraTypeInfo = Column(String)
    filterable = Column(Boolean)
    filteredLookupInfo = Column(String)
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

    def __repr__(self):
        return f"<{self.name} at {self.id}>"


class FileMetadata(Base):
    __tablename__ = "file_metadata"
    id = Column(Integer, primary_key=True)
    schema_revision = Column(Integer, default=-1)
    file_format = Column(Integer, default=1)
