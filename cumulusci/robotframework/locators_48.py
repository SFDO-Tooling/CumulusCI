lex_locators = {
    "actions": "css: ul.oneActionsRibbon",
    "app_launcher": {
        "app_link": "//one-app-launcher-modal//one-app-launcher-app-tile//a[.='{}']",
        "button": "//nav[contains(@class,'appLauncher')]//button[//div[contains(@class,'slds-icon-waffle')]]",
        "current_app": "//div[contains(@class,'navLeft')]//span[contains(@class,'appName')]/span[text()='{}']",
        "menu": "//div[contains(@class, 'appLauncherMenu')]",
        "tab_link": "//one-app-launcher-modal//one-app-launcher-tab-item//a[.='{}']",
        "view_all": "//div[contains(@class, "
        "'appLauncherMenu')]//button[text()='View All']",
    },
    "body": "//div[contains(@class, 'slds-template__container')]/*",
    "desktop_rendered": "css: "
    "div.desktop.container.oneOne.oneAppLayoutHost[data-aura-rendered-by]",
    "loading_box": "css: div.auraLoadingBox.oneLoadingBox",
    "modal": {
        "button": "//div[contains(@class,'uiModal')]//div[contains(@class, "
        "'modal-footer') or contains(@class, "
        "'inlineFooter')]//button[.//*[text()='{}']]",
        "close": "css: button.slds-modal__close",
        "error_messages": "css: div.pageLevelErrors ul.errorsList li",
        "fade_in": "css: div.slds-fade-in-open",
        "has_error": "css: div.pageLevelErrors",
        "is_open": "css: div.uiModal div.panel.slds-modal",
    },
    "object": {
        "button": "css: ul.forceActionsContainer.oneActionsRibbon a[title='{}']",
        "field": "//div[contains(@class, "
        "'uiInput')][.//label[contains(@class, "
        "'uiLabel')][.//span[text()='{}']]]//*[self::input or "
        "self::textarea]",
        "field_label": "//label[@for!='' and "
        "text()='{}']|//label[@for!=''][./span[text()='{}']]",
        "field_lookup_link": "//*[@role='option'][.//*[@title='{}']]",
        "field_lookup_value": "//div[contains(@class, "
        "'uiInput')][.//label[contains(@class, "
        "'uiLabel')][.//span[text()='{}']]]//span[contains(@class,'pillText')]",
        "record_type_option": "//div[contains(@class, "
        "'changeRecordTypeOptionRightColumn')]//span[text()='{}']",
    },
    "popup": {
        "link": "//div[contains(@class, 'uiPopupTarget')][contains(@class, "
        "'visible')]//a[@title='{}']"
    },
    "record": {
        "header": {
            "field": "//li[contains(@class, "
            "'slds-page-header__detail-block')][.//span[contains(@class, "
            "'slds-form-element__label')][@title='{}']]",
            "field_value": "//records-lwc-highlights-panel//force-highlights-details-item[.//*[contains(@class, "
            "'slds-text-title') and "
            "text()='{}']]//p[contains(@class, "
            "'fieldComponent')]//*[text()]",
            "field_value_checked": "//li[contains(@class, "
            "'slds-page-header__detail-block')][.//span[contains(@class, "
            "'slds-form-element__label')][@title='{}']]//span[contains(@class, "
            "'uiOutputCheckbox')]//img[@alt='True']",
            "field_value_link": "//records-lwc-highlights-panel//force-highlights-details-item[.//*[contains(@class, "
            "'slds-text-title') and "
            "text()='{}']]//p[contains(@class, "
            "'fieldComponent')]//a[text()]",
            "field_value_unchecked": "//li[contains(@class, "
            "'slds-page-header__detail-block')][.//span[contains(@class, "
            "'slds-form-element__label')][@title='{}']]//span[contains(@class, "
            "'uiOutputCheckbox')]//img[@alt='False']",
        },
        "related": {
            "button": "//article[contains(@class, "
            "'forceRelatedListCardDesktop')][.//img][.//span[@title='{}']]//a[@title='{}']",
            "card": "//article[contains(@class, "
            "'forceRelatedListCardDesktop')][.//img][.//span[@title='{}']]",
            "count": "//article[contains(@class, "
            "'forceRelatedListCardDesktop')][.//img]//span[@title='{}']/following-sibling::span",
            "link": "//article[contains(@class, "
            "'forceRelatedListCardDesktop')][.//img][.//span[@title='{}']]//*[text()='{}']",
            "popup_trigger": "//article[.//span[@title='{}'][//a[text()='{}']]]//div[contains(@class, "
            "'forceVirtualAction')]/a",
        },
    },
    "spinner": "css: div.slds-spinner",
    "tabs": {"tab": ""},
}
