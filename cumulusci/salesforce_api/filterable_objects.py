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
    "AccountBrandShare",
    "AccountShare",
    "AccountUserTerritory2View",
    "ActionPlanShare",
    "ActionPlanTemplateShare",
    "AgentWorkShare",
    "AnalysisSetupStatusEvent",
    "ApptBundleConfigShare",
    "ApptBundlePolicyShare",
    "AssetShare",
    "AuthorizationFormConsentShare",
    "AuthorizationFormDataUse",
    "AuthorizationFormDataUseHistory",
    "AuthorizationFormDataUseShare",
    "AuthorizationFormShare",
    "BudgetShare",
    "BusinessBrandShare",
    "CalendarViewShare",
    "CampaignShare",
    "CaseShare",
    "ChangeRequestShare",
    "ChannelProgramLevelShare",
    "ChannelProgramMemberShare",
    "ChannelProgramShare",
    "CommSubscriptionChannelTypeShare",
    "CommSubscriptionConsentShare",
    "CommSubscriptionShare",
    "ContactPointAddressShare",
    "ContactPointConsentShare",
    "ContactPointEmailShare",
    "ContactPointPhoneShare",
    "ContactPointTypeConsentShare",
    "ContactRequestShare",
    "ContactShare",
    "ContentUserSubscription",
    "ContentWorkspacePermission",
    "CustomHelpMenuSection",
    "CustomObjectUserLicenseMetrics",
    "CustomPermission",
    "CustomPermissionDependency",
    "CustomerShare",
    "DataIntegrationRecordPurchasePermission",
    "DataPrepServiceLocatorShare",
    "DataUseLegalBasis",
    "DataUseLegalBasisHistory",
    "DataUseLegalBasisShare",
    "DataUsePurpose",
    "DataUsePurposeHistory",
    "DataUsePurposeShare",
    "DatasetAccess",
    "DelegatedAccountShare",
    "DialerCallUsageShare",
    "DocumentChecklistItemShare",
    "EngagementChannelTypeShare",
    "ExpenseReportShare",
    "ExpenseShare",
    "ExternalDataUserAuth",
    "ExternalEventMappingShare",
    "FieldPermissions",
    "FlowInterviewLogShare",
    "FlowInterviewShare",
    "FlowTestResultShare",
    "ForecastingShare",
    "ForecastingUserPreference",
    "Group",
    "GroupMember",
    "ImageShare",
    "IncidentShare",
    "IndividualShare",
    "JobProfileShare",
    "KnowledgeableUser",
    "LeadShare",
    "ListEmailShare",
    "LiveAgentSessionShare",
    "LiveChatObjectAccessConfig",
    "LiveChatObjectAccessDefinition",
    "LiveChatTranscriptShare",
    "LiveChatUserConfig",
    "LiveChatUserConfigProfile",
    "LiveChatUserConfigUser",
    "LocationShare",
    "LocationTrustMeasureShare",
    "MacroShare",
    "MacroUsageShare",
    "MaintenancePlanShare",
    "MaintenanceWorkRuleShare",
    "MessagingEndUser",
    "MessagingEndUserHistory",
    "MessagingEndUserShare",
    "MessagingSessionShare",
    "MutingPermissionSet",
    "NetworkUserHistoryRecent",
    "ObjectPermissions",
    "OmniSupervisorConfigUser",
    "OpportunityShare",
    "OrderShare",
    "OutgoingEmail",
    "OutgoingEmailRelation",
    "PartnerFundAllocationShare",
    "PartnerFundClaimShare",
    "PartnerFundRequestShare",
    "PartnerMarketingBudgetShare",
    "PartyConsentShare",
    "PendingServiceRoutingShare",
    "PermissionSet",
    "PermissionSetAssignment",
    "PermissionSetGroup",
    "PermissionSetGroupComponent",
    "PermissionSetLicense",
    "PermissionSetLicenseAssign",
    "PermissionSetTabSetting",
    "PortalDelegablePermissionSet",
    "PresenceUserConfig",
    "PresenceUserConfigProfile",
    "PresenceUserConfigUser",
    "PricebookShare",
    "ProblemShare",
    "ProcessExceptionShare",
    "ProductItemShare",
    "ProductRequestShare",
    "ProductServiceCampaignShare",
    "ProductTransferShare",
    "ProfileSkillShare",
    "ProfileSkillUser",
    "ProfileSkillUserFeed",
    "ProfileSkillUserHistory",
    "PromptActionShare",
    "PromptErrorShare",
    "QuickTextShare",
    "QuickTextUsageShare",
    "QuoteShare",
    "RecordsetFilterCriteriaShare",
    "RecurrenceScheduleShare",
    "ReturnOrderShare",
    "SOSSessionShare",
    "SchedulingConstraintShare",
    "ScorecardShare",
    "SellerShare",
    "ServiceAppointmentShare",
    "ServiceContractShare",
    "ServiceCrewShare",
    "ServiceResourcePreferenceShare",
    "ServiceResourceShare",
    "ServiceTerritoryShare",
    "SetupEntityAccess",
    "SharingRecordCollectionShare",
    "SharingUserCoverage",
    "ShiftPatternShare",
    "ShiftShare",
    "ShiftTemplateShare",
    "ShipmentShare",
    "SkillUser",
    "SocialPostShare",
    "StreamingChannelShare",
    "SurveyEngagementContextShare",
    "SurveyInvitationShare",
    "SurveyShare",
    "TimeSheetShare",
    "TodayGoalShare",
    "TopicUserEvent",
    "TranslationUser",
    "TravelModeShare",
    "User",
    "UserAccountTeamMember",
    "UserAppInfo",
    "UserAppMenuCustomization",
    "UserAppMenuCustomizationShare",
    "UserAppMenuItem",
    "UserChangeEvent",
    "UserConfigTransferButton",
    "UserConfigTransferSkill",
    "UserCustomBadge",
    "UserCustomBadgeLocalization",
    "UserEmailPreferredPerson",
    "UserEmailPreferredPersonShare",
    "UserEntityAccess",
    "UserFeed",
    "UserFieldAccess",
    "UserLicense",
    "UserListView",
    "UserListViewCriterion",
    "UserLogin",
    "UserNavItem",
    "UserPackageLicense",
    "UserPermissionAccess",
    "UserPreference",
    "UserProvAccount",
    "UserProvAccountStaging",
    "UserProvMockTarget",
    "UserProvisioningConfig",
    "UserProvisioningLog",
    "UserProvisioningRequest",
    "UserProvisioningRequestShare",
    "UserRecordAccess",
    "UserRole",
    "UserServicePresence",
    "UserServicePresenceShare",
    "UserSetupAppInfo",
    "UserSetupEntityAccess",
    "UserShare",
    "UserTeamMember",
    "UserTerritory2Association",
    "VideoCallShare",
    "VisualforceAccessMetrics",
    "VoiceCallShare",
    "WarrantyTermShare",
    "WorkAccess",
    "WorkAccessShare",
    "WorkBadgeDefinitionShare",
    "WorkOrderShare",
    "WorkPlanSelectionRuleShare",
    "WorkPlanShare",
    "WorkPlanTemplateShare",
    "WorkStepTemplateShare",
    "WorkThanksShare",
    "WorkTypeGroupShare",
    "WorkTypeShare",
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
#     "OpportunityShare",
#     "OrderShare",
#     "OutgoingEmail",
#     "OutgoingEmailRelation",
# )

# And this code:
#
# patterns_to_ignore = NOT_EXTRACTABLE_WITHOUT_NOT_COUNTABLE

# names = [obj["name"] for obj in sf.describe()["sobjects"]]

# regexps_to_ignore = [
#     re.compile(pat.replace("%", ".*"), re.IGNORECASE) for pat in patterns_to_ignore
# ]

# for name in names:
#     if any(reg.match(name) for reg in regexps_to_ignore) and not ("__" in name):
#         print(name)
