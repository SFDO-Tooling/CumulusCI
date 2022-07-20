NOT_COUNTABLE = (
    "ContentDocumentLink",  # ContentDocumentLink requires a filter by a single Id on ContentDocumentId or LinkedEntityId
    "ContentFolderItem",  # Implementation restriction: ContentFolderItem requires a filter by Id or ParentContentFolderId
    "ContentFolder",  # Similar to above
    "ContentFolderLink",  # Similar to above
    "ContentFolderMember",  # Similar to above
    "IdeaComment",  # you must filter using the following syntax: CommunityId = [single ID],
    "Vote",  # you must filter using the following syntax: ParentId = [single ID],
    "RecordActionHistory",  # Gack: 1133111327-118855 (1126216936)
)


NOT_EXTRACTABLE = NOT_COUNTABLE + (
    "%Share",
    "%Access",
    "%History",
    "%Permission",
    "%PermissionSet",
    "%Permissions",
    "AuthorizationFormDataUse",
    "CustomHelpMenuSection",
    "DataUseLegalBasis",
    "DataUsePurpose",
    "ExternalDataUserAuth",
    "FieldPermissions",
    "Group",
    "GroupMember",
    "PermissionSet",
    "PermissionSetAssignment",
    "PermissionSetGroup",
    "PermissionSetGroupComponent",
    "PermissionSetLicenseAssign",
    "PermissionSetTabSetting",
    "User",
    "UserAppInfo",
    "UserAppMenuCustomization",
    "UserCustomBadge",
    "UserCustomBadgeLocalization",
    "UserEmailPreferredPerson",
    "UserListView",
    "UserListViewCriterion",
    "UserPackageLicense",
    "UserPreference",
    "UserProvAccount",
    "UserProvAccountStaging",
    "UserProvMockTarget",
    "UserProvisioningConfig",
    "UserProvisioningLog",
    "UserProvisioningRequest",
    "UserRole",
)

# Generated with these patterns:
#     "%permission%",
#     "%use%",
#     "%access%",
#     "group",
#     "%share",
#     "NetworkUserHistoryRecent",
#     "ObjectPermissions",
#     "OmniSupervisorConfigUser",
#     "OutgoingEmail",
#     "OutgoingEmailRelation",
# )

# And this code:
#
# patterns_to_ignore = NOT_EXTRACTABLE_WITHOUT_NOT_COUNTABLE

# names = [obj["name"] for obj in sf.describe()["sobjects"] if obj["createable"]]

# regexps_to_ignore = [
#     re.compile(pat.replace("%", ".*"), re.IGNORECASE) for pat in patterns_to_ignore
# ]

# for name in names:
#     if any(reg.match(name) for reg in regexps_to_ignore) and not ("__" in name):
#         print(name)
