from .extract_yml import ExtractDeclaration

_DEFAULT_DECLARATIONS = [
    ExtractDeclaration(
        sf_object="Account", where="Name != 'Sample Account for Entitlements'"
    ),
    ExtractDeclaration(sf_object="BusinessHours", where="Name != 'Default'"),
    ExtractDeclaration(sf_object="ContentWorkspace", where="Name != 'Asset Library'"),
    ExtractDeclaration(sf_object="Entitlement", where="Name != 'Sample Entitlement'"),
    ExtractDeclaration(
        sf_object="FieldServiceMobileSettings",
        where="DeveloperName != 'Field_Service_Mobile_Settings'",
    ),
    ExtractDeclaration(
        sf_object="PricebookEntry",
        where="Pricebook2.Id != NULL and Pricebook2.Name != 'Standard Price Book'",
    ),
    ExtractDeclaration(sf_object="Pricebook2", where="Name != 'Standard Price Book'"),
    ExtractDeclaration(
        sf_object="WebLink", where="Name != 'ViewCampaignInfluenceReport'"
    ),
    ExtractDeclaration(
        sf_object="Folder",
        where="DeveloperName NOT IN ('SharedApp', 'EinsteinBotReports')",
    ),
    ExtractDeclaration(
        sf_object="MilestoneType",
        where="Name NOT IN ('First Response to Customer', 'Escalate Case', 'Close Case')",
    ),
    ExtractDeclaration(
        sf_object="WorkBadgeDefinition",
        where="Name NOT IN ('Thanks', 'You\\'re a RockStar!', 'Team Player',"
        "'All About Execution', 'Teacher', 'Top Performer', 'Hot Lead',"
        "'Key Win', 'Customer Hero', 'Competition Crusher',"
        "'Deal Maker', 'Gold Star')",
    ),
    ExtractDeclaration(
        sf_object="EmailTemplate",
        where="DeveloperName NOT IN ('CommunityLockoutEmailTemplate',"
        "'CommunityVerificationEmailTemplate',"
        "'CommunityChgEmailVerOldTemplate',"
        "'CommunityChgEmailVerNewTemplate',"
        "'CommunityDeviceActEmailTemplate',"
        "'CommunityWelcomeEmailTemplate',"
        "'CommunityChangePasswordEmailTemplate',"
        "'CommunityForgotPasswordEmailTemplate' )",
    ),
]
DEFAULT_DECLARATIONS = {decl.sf_object: decl for decl in _DEFAULT_DECLARATIONS}
