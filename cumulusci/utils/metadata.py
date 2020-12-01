from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple
import pathlib
import shutil

from cumulusci.core.config import UniversalConfig
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.metadata.package import metadata_sort_key
from cumulusci.utils.xml import metadata_tree
from cumulusci.utils.xml.metadata_tree import MetadataElement


TypeMembers = Dict[str, List[str]]


class MetadataProcessor:
    def __init__(
        self,
        type_name: Optional[str],
        extension: str = None,
        additional: Dict[str, str] = None,
    ):
        self.type_name = type_name
        self.extension = extension
        self.additional = additional or {}

    def __iter__(self):
        """hack to make it simpler to construct MD_PROCESSORS below

        (so that a single MetadataProcessor instance can pass type checking
        for Iterable[MetadataProcessor])
        """
        return iter((self,))

    def collect_members(self, path: pathlib.Path) -> TypeMembers:
        """List metadata components found in this path."""
        types = defaultdict(list)
        for item in sorted(path.iterdir()):
            if item.name.startswith("."):
                continue

            for mdtype, members in self.collect_members_from_subpath(item).items():
                types[mdtype].extend(members)

        return types

    def collect_members_from_subpath(self, path: pathlib.Path) -> TypeMembers:
        if self.extension and not path.name.endswith(self.extension):
            return {}

        parent_name = self._strip_extension(path.name).replace(
            "___NAMESPACE___", "%%%NAMESPACE%%%"
        )

        types = defaultdict(list)
        # Include the component represented by the file as a whole,
        # unless it may contain additional separate components,
        # in which case we need to check the file contents.
        include_parent = not bool(self.additional)
        if not include_parent:
            # Scan XML and add each additional component.
            # If any element is not an additional component, include the parent.
            tree = metadata_tree.parse(path)
            for el in tree.iterchildren():
                if el.tag in self.additional:
                    mdtype = self.additional[el.tag]
                    name = f"{parent_name}.{el.fullName.text}"
                    types[mdtype].append(name)
                else:
                    include_parent = True
        if include_parent and self.type_name is not None:
            types[self.type_name].append(parent_name)

        return types

    def _strip_extension(self, name: str):
        if self.extension and name.endswith(self.extension):
            name = name[: -len(self.extension)]
        return name

    def merge(self, path: pathlib.Path, src: pathlib.Path, target: pathlib.Path):
        """Merge metadata components into another package."""
        # Make sure metadata folder exists in target package
        (target / path.relative_to(src)).mkdir(parents=True, exist_ok=True)

        for item in path.iterdir():
            if item.name.startswith("."):
                continue

            relative_path = item.relative_to(src)
            target_item_path = target / relative_path

            if self.extension and item.name.endswith(self.extension):
                # merge metadata xml
                self._merge_xml(item, target_item_path)
            else:
                # copy entire folder or file
                if target_item_path.exists():
                    shutil.rmtree(str(target_item_path))
                copy_op = shutil.copytree if item.is_dir() else shutil.copy
                copy_op(str(item), str(target_item_path))

    def _merge_xml(self, src: pathlib.Path, target: pathlib.Path):
        src_tree = metadata_tree.parse(src)

        # Load or create destination file
        if target.exists():
            target_tree = metadata_tree.parse(target)
        else:
            target_tree = MetadataElement(src_tree.tag)

        additional_metadata_tags = set(self.additional)
        src_has_primary_metadata = any(
            el.tag not in additional_metadata_tags for el in src_tree.iterchildren()
        )

        # First do a pass through the destination file
        # to produce a new list of children that:
        # - preserves elements which are additional metadata types
        # - replaces elements which are not additional metadata types
        #   with the corresponding tags from the source file
        # - keeps existing tags in the same position
        merged_tree = MetadataElement(target_tree.tag)
        for el in target_tree.iterchildren():
            if el.tag in additional_metadata_tags or not src_has_primary_metadata:
                merged_tree.append(el)
            else:
                # If src includes any elements which are not additional metadata,
                # replace all non-additional elements in dest with the corresponding ones from src.
                for el in src_tree.findall(el.tag):
                    # NB this has the side effect of removing them from src_tree,
                    # which we want in order to avoid appending them again below.
                    merged_tree.append(el)

        # Now do a pass through src_tree to handle any tags that were not yet in dest_tree:
        # - additional metadata: replace or append, matching on fullName
        # - non-additional metadata: append
        for el in list(src_tree.iterchildren()):
            if el.tag in additional_metadata_tags:
                existing_el = merged_tree.find(el.tag, fullName=el.fullName.text)
                if existing_el is not None:
                    merged_tree.replace(existing_el, el)
                    continue
            merged_tree.append(el)

        # write merged file
        target.write_text(merged_tree.tostring())


class FolderMetadataProcessor(MetadataProcessor):
    type_name: str

    def collect_members_from_subpath(self, path: pathlib.Path) -> TypeMembers:
        name = path.name
        members = []

        # Add the folder itself if there's a -meta.xml file
        if pathlib.Path(str(path) + "-meta.xml").exists():
            members.append(name)

        # Ignore non-folders
        if not path.is_dir():
            return {}

        # Add subitems
        for subpath in sorted(path.iterdir()):
            subname = subpath.name
            if self.extension and not subname.endswith(self.extension):
                continue
            if subname.endswith("-meta.xml"):
                continue
            subname = self._strip_extension(subname)
            members.append(f"{name}/{subname}")

        return {self.type_name: members}

    def merge(self, path: pathlib.Path, src: pathlib.Path, target: pathlib.Path):
        # Copy each component's file to the corresponding path in the target package.
        members = self.collect_members(path)
        for name in members[self.type_name]:
            if "/" in name:
                item = path / (name + (self.extension or ""))
            else:
                # folder -- only need to copy the -meta.xml
                item = path / (name + "-meta.xml")
            relpath = item.relative_to(src)
            (target / relpath).parent.mkdir(parents=True, exist_ok=True)
            if not item.is_dir():
                shutil.copy(str(item), str(target / relpath))
            meta_xml = item.parent / (item.name + "-meta.xml")
            if meta_xml.exists():
                shutil.copy(str(meta_xml), str(target / relpath) + "-meta.xml")


class BundleMetadataProcessor(MetadataProcessor):
    type_name: str

    def collect_members_from_subpath(self, path: pathlib.Path) -> TypeMembers:
        if path.is_dir():
            return {self.type_name: [path.name]}
        return {}


def _iter_processors(
    path: pathlib.Path,
) -> Iterable[Tuple[pathlib.Path, MetadataProcessor]]:
    """Gets a processor for each folder in a metadata package"""
    for item in path.iterdir():
        if item.name.startswith(".") or not item.is_dir():
            continue
        try:
            processors = MD_PROCESSORS[item.name]
        except KeyError:
            raise CumulusCIException(f"Unexpected folder in metadata package: {item}")
        for processor in processors:
            yield item, processor


class MetadataPackage:
    """Represents a Salesforce metadata package
    https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_package.htm
    """

    def __init__(self, types: TypeMembers = None, version: str = None):
        self.types = defaultdict(list)
        for k, v in types.items():
            self.types[k] = v
        self.version = version or UniversalConfig().package__api_version

    @classmethod
    def from_path(cls, path: pathlib.Path) -> "MetadataPackage":
        version = None
        manifest_path = path / "package.xml"
        if manifest_path.exists():
            manifest = metadata_tree.parse(manifest_path)
            version = str(manifest.version.text)

        types: TypeMembers = {}
        for folder_path, processor in _iter_processors(path):
            types.update(processor.collect_members(folder_path))
        return MetadataPackage(types, version)

    def write_manifest(self, path: pathlib.Path) -> None:
        manifest_path = path / "package.xml"
        manifest = MetadataElement("Package")
        for name, members in sorted(self.types.items()):
            types = MetadataElement("types")
            for member in sorted(members, key=metadata_sort_key):
                types.append("members", member)
            manifest.append(types)
        manifest.append("version", self.version)
        manifest_path.write_text(manifest.tostring(xml_declaration=True))


def write_manifest(components: TypeMembers, api_version, path: pathlib.Path) -> None:
    """Write package.xml including components to the specified path."""
    MetadataPackage(components, api_version).write_manifest(path)


def update_manifest(path: pathlib.Path) -> None:
    """Generate package.xml based on actual metadata present in a folder."""
    MetadataPackage.from_path(path).write_manifest(path)


def merge_metadata(
    src: pathlib.Path, dest: pathlib.Path, update_manifest=update_manifest
) -> None:
    """Merge one metadata package into another.

    The merging logic for each subfolder is delegated to a MetadataProcessor.
    """
    for folder_path, processor in _iter_processors(src):
        processor.merge(folder_path, src, dest)

    if update_manifest:
        update_manifest(dest)


MD_PROCESSORS: Dict[str, Iterable[MetadataProcessor]] = {
    "accountRelationshipShareRules": MetadataProcessor(
        "AccountRelationshipShareRule", ".accountRelationshipShareRule"
    ),
    "actionLinkGroupTemplates": MetadataProcessor(
        "ActionLinkGroupTemplate", ".actionLinkGroupTemplate"
    ),
    "actionPlanTemplates": MetadataProcessor("ActionPlanTemplate", ".apt"),
    "analyticSnapshots": MetadataProcessor("AnalyticSnapshot", ".analyticsnapshot"),
    "animationRules": MetadataProcessor("AnimationRule", ".animationRule"),
    "apexEmailNotifications": MetadataProcessor(
        "ApexEmailNotification", ".notifications"
    ),
    "applications": MetadataProcessor("CustomApplication", ".app"),
    "appMenus": MetadataProcessor("AppMenu", ".appMenu"),
    "appointmentSchedulingPolicies": MetadataProcessor(
        "AppointmentSchedulingPolicy", ".policy"
    ),
    "approvalProcesses": MetadataProcessor("ApprovalProcess", ".approvalProcess"),
    "assignmentRules": MetadataProcessor("AssignmentRules", ".assignmentRules"),
    "audience": MetadataProcessor("Audience", ".audience"),
    "aura": BundleMetadataProcessor("AuraDefinitionBundle"),
    "authproviders": MetadataProcessor("AuthProvider", ".authprovider"),
    "autoResponseRules": MetadataProcessor("AutoResponseRules", ".autoResponseRules"),
    "blacklistedConsumers": MetadataProcessor(
        "BlacklistedConsumer", ".blacklistedConsumer"
    ),
    "bot": MetadataProcessor("Bot", ".bot", {"botVersions": "BotVersion"}),
    "brandingSets": MetadataProcessor("BrandingSet", ".brandingSet"),
    "businessProcessGroups": MetadataProcessor(
        "BusinessProcessGroup", ".businessProcessGroup"
    ),
    "cachePartitions": MetadataProcessor("PlatformCachePartition", ".cachePartition"),
    "callCenters": MetadataProcessor("CallCenter", ".callCenter"),
    "CallCoachingMediaProviders": MetadataProcessor(
        "CallCoachingMediaProvider", ".callCoachingMediaProvider"
    ),
    "campaignInfluenceModels": MetadataProcessor(
        "CampaignInfluenceModel", ".campaignInfluenceModel"
    ),
    "CaseSubjectParticles": MetadataProcessor(
        "CaseSubjectParticle", ".caseSubjectParticle"
    ),
    "certs": MetadataProcessor("Certificate", ".crt-meta.xml"),
    "channelLayouts": MetadataProcessor("ChannelLayout", ".channelLayout"),
    "ChatterExtensions": MetadataProcessor("ChatterExtension", ".ChatterExtension"),
    "classes": MetadataProcessor("ApexClass", ".cls-meta.xml"),
    "cleanDataServices": MetadataProcessor("CleanDataService", ".cleanDataService"),
    "cmsConnectSource": MetadataProcessor("CMSConnectSource", ".cmsConnectSource"),
    "communities": MetadataProcessor("Community", ".community"),
    "communityTemplateDefinitions": MetadataProcessor(
        "CommunityTemplateDefinition", ".communityTemplateDefinition"
    ),
    "communityThemeDefinitions": MetadataProcessor(
        "CommunityThemeDefinition", ".communityThemeDefinition"
    ),
    "components": MetadataProcessor("ApexComponent", ".component-meta.xml"),
    "connectedApps": MetadataProcessor("ConnectedApp", ".connectedApp"),
    "contentassets": MetadataProcessor("ContentAsset", ".asset-meta.xml"),
    "corswhitelistorigins": MetadataProcessor(
        "CorsWhitelistOrigin", ".corswhitelistorigin"
    ),
    "cspTrustedSites": MetadataProcessor("CspTrustedSite", ".cspTrustedSite"),
    "customApplicationComponent": MetadataProcessor(
        "CustomApplicationComponent", ".customApplicationComponent"
    ),
    "customHelpMenuSections": MetadataProcessor(
        "CustomHelpMenuSection", ".customHelpMenuSection"
    ),
    "customMetadata": MetadataProcessor("CustomMetadata", ".md"),
    "customPermissions": MetadataProcessor("CustomPermission", ".customPermission"),
    "dashboards": FolderMetadataProcessor("Dashboard", ".dashboard"),
    "datacategorygroups": MetadataProcessor("DataCategoryGroup", ".datacategorygroup"),
    "dataStreamDefinitions": MetadataProcessor(
        "DataStreamDefinition", ".dataStreamDefinition"
    ),
    "dataSources": MetadataProcessor("ExternalDataSource", ".dataSource"),
    "delegateGroups": MetadataProcessor("DelegateGroup", ".delegateGroup"),
    "documents": FolderMetadataProcessor("Document"),
    "duplicateRules": MetadataProcessor("DuplicateRule", ".duplicateRule"),
    "eclair": MetadataProcessor("EclairGeoData", ".geodata"),
    "email": FolderMetadataProcessor("EmailTemplate", ".email"),
    "emailservices": MetadataProcessor("EmailServicesFunction", ".xml"),
    "EmbeddedServiceBranding": MetadataProcessor(
        "EmbeddedServiceBranding", ".EmbeddedServiceBranding"
    ),
    "EmbeddedServiceConfig": MetadataProcessor(
        "EmbeddedServiceConfig", ".EmbeddedServiceConfig"
    ),
    "EmbeddedServiceFieldService": MetadataProcessor(
        "EmbeddedServiceFieldService", ".EmbeddedServiceFieldService"
    ),
    "EmbeddedServiceFlowConfig": MetadataProcessor(
        "EmbeddedServiceFlowConfig", ".EmbeddedServiceFlowConfig"
    ),
    "EmbeddedServiceLiveAgent": MetadataProcessor(
        "EmbeddedServiceLiveAgent",
        ".EmbeddedServiceLiveAgent",
    ),
    "EmbeddedServiceMenuSettings": MetadataProcessor(
        "EmbeddedServiceMenuSettings", ".EmbeddedServiceMenuSettings"
    ),
    "entitlementProcesses": MetadataProcessor(
        "EntitlementProcess", ".entitlementProcess"
    ),
    "entitlementTemplates": MetadataProcessor(
        "EntitlementTemplate", ".entitlementTemplate"
    ),
    "escalationRules": MetadataProcessor("EscalationRules", ".escalationRules"),
    "experiences": BundleMetadataProcessor("ExperienceBundle"),
    "externalServiceRegistrations": MetadataProcessor(
        "ExternalServiceRegistration", ".externalServiceRegistration"
    ),
    "featureParameters": (
        MetadataProcessor("FeatureParameterBoolean", ".featureParameterBoolean"),
        MetadataProcessor("FeatureParameterDate", ".featureParameterDate"),
        MetadataProcessor("FeatureParameterInteger", ".featureParameterInteger"),
    ),
    "feedFilters": MetadataProcessor("CustomFeedFilter", ".feedFilter"),
    "flexipages": MetadataProcessor("FlexiPage", ".flexipage"),
    "flows": MetadataProcessor("Flow", ".flow"),
    "flowCategories": MetadataProcessor("FlowCategory", ".flowCategory"),
    "flowDefinitions": MetadataProcessor("FlowDefinition", ".flowDefinition"),
    "globalPicklist": MetadataProcessor("GlobalPicklist", ".globalPicklist"),
    "globalValueSets": MetadataProcessor("GlobalValueSet", ".globalValueSet"),
    "globalValueSetTranslations": MetadataProcessor(
        "GlobalValueSetTranslation", ".globalValueSetTranslation"
    ),
    "groups": MetadataProcessor("Group", ".group"),
    "homepagecomponents": MetadataProcessor("HomePageComponent", ".homePageComponent"),
    "homePageLayouts": MetadataProcessor("HomePageLayout", ".homePageLayout"),
    "inboundCertificate": MetadataProcessor(
        "InboundCertificate", ".inboundCertificate"
    ),
    "labels": MetadataProcessor("CustomLabels", ".labels"),
    "layouts": MetadataProcessor("Layout", ".layout"),
    "letterhead": MetadataProcessor("Letterhead", ".letter"),
    "lightningBolts": MetadataProcessor("LightningBolt", ".lightningBolt"),
    "lightningExperienceThemes": MetadataProcessor(
        "LightningExperienceTheme", ".lightningExperienceTheme"
    ),
    "LightningOnboardingConfigs": MetadataProcessor(
        "LightningOnboardingConfig", ".lightningOnboardingConfig"
    ),
    "liveChatAgentConfigs": MetadataProcessor(
        "LiveChatAgentConfig", ".liveChatAgentConfig"
    ),
    "liveChatButtons": MetadataProcessor("LiveChatButton", ".liveChatButton"),
    "liveChatDeployments": MetadataProcessor(
        "LiveChatDeployment", ".liveChatDeployment"
    ),
    "liveChatSensitiveDataRule": MetadataProcessor(
        "LiveChatSensitiveDataRule", ".liveChatSensitiveDataRule"
    ),
    "lwc": BundleMetadataProcessor("LightningComponentBundle"),
    "managedContentTypes": MetadataProcessor(
        "ManagedContentType", ".managedContentType"
    ),
    "managedTopics": MetadataProcessor("ManagedTopics", ".managedTopics"),
    "matchingRules": MetadataProcessor(
        None,
        ".matchingRule",
        {
            "matchingRules": "MatchingRule",
        },
    ),
    "messageChannels": MetadataProcessor("LightningMessageChannel", ".messageChannel"),
    "milestoneTypes": MetadataProcessor("MilestoneType", ".milestoneType"),
    "mktDataSources": MetadataProcessor("DataSource", ".dataSource"),
    "mktDataSourceObjects": MetadataProcessor("DataSourceObject", ".dataSourceObject"),
    "mktDataTranObjects": MetadataProcessor("MktDataTranObject", ".mktDataTranObject"),
    "mlDomains": MetadataProcessor("MlDomain", ".mlDomain"),
    "moderation": [
        MetadataProcessor("KeywordList", ".keywords"),
        MetadataProcessor("ModerationRule", ".rule"),
    ],
    "mutingpermissionsets": MetadataProcessor(
        "MutingPermissionSet", ".mutingpermissionset"
    ),
    "myDomainDiscoverableLogins": MetadataProcessor(
        "MyDomainDiscoverableLogin", ".myDomainDiscoverableLogin"
    ),
    "namedCredentials": MetadataProcessor("NamedCredential", ".namedCredential"),
    "navigationMenus": MetadataProcessor("NavigationMenu", ".navigationMenu"),
    "networks": MetadataProcessor("Network", ".network"),
    "networkBranding": MetadataProcessor(
        "NetworkBranding", ".networkBranding-meta.xml"
    ),
    "notificationtypes": MetadataProcessor("CustomNotificationType", ".notiftype"),
    "notificationTypeConfig": MetadataProcessor("NotificationTypeConfig", ".config"),
    "oauthcustomscopes": MetadataProcessor("OauthCustomScope", ".oauthcustomscope"),
    "objects": MetadataProcessor(
        "CustomObject",
        ".object",
        {
            "businessProcesses": "BusinessProcess",
            "compactLayouts": "CompactLayout",
            "fields": "CustomField",
            "fieldSets": "FieldSet",
            "indexes": "Index",
            "listViews": "ListView",
            "namedFilters": "NamedFilter",
            "recordTypes": "RecordType",
            "sharingReasons": "SharingReason",
            "validationRules": "ValidationRule",
            "webLinks": "WebLink",
        },
    ),
    "objectTranslations": MetadataProcessor(
        "CustomObjectTranslation", ".objectTranslation"
    ),
    "pages": MetadataProcessor("ApexPage", ".page-meta.xml"),
    "pathAssistants": MetadataProcessor("PathAssistant", ".pathAssistant"),
    "paymentGatewayProviders": MetadataProcessor(
        "PaymentGatewayProvider", ".paymentGatewayProfider"
    ),
    "permissionsets": MetadataProcessor("PermissionSet", ".permissionset"),
    "permissionsetgroups": MetadataProcessor(
        "PermissionSetGroup", ".permissionsetgroup"
    ),
    "platformEventChannels": MetadataProcessor(
        "PlatformEventChannel", ".platformEventChannel"
    ),
    "platformEventChannelMembers": MetadataProcessor(
        "PlatformEventChannelMember", ".platformEventChannelMember"
    ),
    "portals": MetadataProcessor("Portal", ".portal"),
    "postTemplates": MetadataProcessor("PostTemplate", ".postTemplate"),
    "presenceDeclineReasons": MetadataProcessor(
        "PresenceDeclineReason", ".presenceDeclineReason"
    ),
    "presenceUserConfigs": MetadataProcessor(
        "PresenceUserConfig", ".presenceUserConfig"
    ),
    "profiles": MetadataProcessor("Profile", ".profile"),
    "profilePasswordPolicies": MetadataProcessor(
        "ProfilePasswordPolicy", ".profilePasswordPolicy"
    ),
    "profileSessionSettings": MetadataProcessor(
        "ProfileSessionSetting", ".profileSessionSetting"
    ),
    "prompts": MetadataProcessor("Prompt", ".prompt"),
    "queues": MetadataProcessor("Queue", ".queue"),
    "queueRoutingConfigs": MetadataProcessor(
        "QueueRoutingConfig", ".queueRoutingConfig"
    ),
    "quickActions": MetadataProcessor("QuickAction", ".quickAction"),
    "recommendationStrategies": MetadataProcessor(
        "RecommendationStrategy", ".recommendationStrategy"
    ),
    "recordActionDeployments": MetadataProcessor(
        "RecordActionDeployment", ".deployment"
    ),
    "redirectWhitelistUrls": MetadataProcessor(
        "RedirectWhitelistUrl", ".redirectWhitelistUrl"
    ),
    "remoteSiteSettings": MetadataProcessor("RemoteSiteSetting", ".remoteSite"),
    "reports": FolderMetadataProcessor("Report", ".report"),
    "reportTypes": MetadataProcessor("ReportType", ".reportType"),
    "roles": MetadataProcessor("Role", ".role"),
    "rules": MetadataProcessor("Territory2Rule", ".territory2Rule"),
    "salesworkqueuesettings": MetadataProcessor(
        "SalesWorkQueueSettings", ".salesworkqueuesetting"
    ),
    "samlssoconfigs": MetadataProcessor("SamlSsoConfig", ".samlssoconfig"),
    "scontrols": MetadataProcessor("Scontrol", ".scf-meta.xml"),
    "serviceChannels": MetadataProcessor("ServiceChannel", ".serviceChannel"),
    "servicePresenceStatuses": MetadataProcessor(
        "ServicePresenceStatus", ".servicePresenceStatus"
    ),
    "settings": MetadataProcessor("Settings", ".settings"),
    "sharingRules": MetadataProcessor(
        None,
        ".sharingRules",
        {
            "sharingCriteriaRules": "SharingCriteriaRule",
            "sharingGuestRules": "SharingGuestRule",
            "sharingOwnerRules": "SharingOwnerRule",
            "sharingTerritoryRules": "SharingTerritoryRule",
        },
    ),
    "sharingSets": MetadataProcessor("SharingSet", ".sharingSet"),
    "standardValueSets": MetadataProcessor("StandardValueSet", ".standardValueSet"),
    "standardValueSetTranslations": MetadataProcessor(
        "StandardValueSetTranslation", ".standardValueSetTranslation"
    ),
    "staticresources": MetadataProcessor("StaticResource", ".resource-meta.xml"),
    "siteDotComSites": MetadataProcessor("SiteDotCom", ".site-meta.xml"),
    "sites": MetadataProcessor("CustomSite", ".site"),
    "skills": MetadataProcessor("Skill", ".skill"),
    "synonymDictionaries": MetadataProcessor("SynonymDictionary", ".synonymDictionary"),
    "tabs": MetadataProcessor("CustomTab", ".tab"),
    "territories": [
        MetadataProcessor("Territory", ".territory"),
        MetadataProcessor("Territory2", ".territory2"),
    ],
    "territory2Models": MetadataProcessor("Territory2Model", ".territory2Model"),
    "territory2Types": MetadataProcessor("Territory2Type", ".territory2Type"),
    "testSuites": MetadataProcessor("ApexTestSuite", ".testSuite"),
    "timeSheetTemplates": MetadataProcessor("TimeSheetTemplate", ".timeSheetTemplate"),
    "topicsForObjects": MetadataProcessor("TopicsForObjects", ".topicsForObjects"),
    "transactionSecurityPolicies": MetadataProcessor(
        "TransactionSecurityPolicy", ".transactionSecurityPolicy"
    ),
    "translations": MetadataProcessor("Translations", ".translation"),
    "triggers": MetadataProcessor("ApexTrigger", ".trigger-meta.xml"),
    "userAuthCertificates": MetadataProcessor(
        "UserAuthCertificate", ".userAuthCertificate"
    ),
    "UserCriteria": MetadataProcessor("UserCriteria", ".userCriteria"),
    "UserProvisioningConfigs": MetadataProcessor(
        "UserProvisioningConfig", ".userProvisioningConfig"
    ),
    "wave": [
        MetadataProcessor("WaveApplication", ".wapp"),
        MetadataProcessor("WaveDashboard", ".wdash"),
        MetadataProcessor("WaveDataflow", ".wdf"),
        MetadataProcessor("WaveDataset", ".wds"),
        MetadataProcessor("WaveLens", ".wlens"),
        MetadataProcessor("WaveRecipe", ".wdpr"),
        MetadataProcessor("WaveXmd", ".xmd"),
    ],
    "waveTemplates": BundleMetadataProcessor("WaveTemplateBundle"),
    "weblinks": MetadataProcessor("CustomPageWebLink", ".weblink"),
    "webstoretemplate": MetadataProcessor("WebStoreTemplate", ".webstoretemplate"),
    "workflows": MetadataProcessor(
        None,
        ".workflow",
        {
            "alerts": "WorkflowAlert",
            "fieldUpdates": "WorkflowFieldUpdate",
            "outboundMessages": "WorkflowOutboundMessage",
            "rules": "WorkflowRule",
            "tasks": "WorkflowTask",
        },
    ),
    "workSkillRoutings": MetadataProcessor("WorkSkillRouting", ".workSkillRouting"),
}

# To do:
# - functional testing
# - preserve package settings
# - destructive?
# - use it to generate package.xml elsewhere
# - comments
