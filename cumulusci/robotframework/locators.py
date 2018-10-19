lex_locators = {
    "app_launcher": {
        "app_link": "//div[@class='slds-section slds-is-open salesforceIdentityAppLauncherDesktopInternal']//section[@id='cards']//a[@class='appTileTitle' and text()='{}']",
        "button": "//nav[contains(@class,'appLauncher')]//button[//div[contains(@class,'slds-icon-waffle')]]",
        "current_app": "//div[contains(@class,'navLeft')]//span[contains(@class,'appName')]/span[text()='{}']",
        "tab_link": "css: a.app-launcher-link[title='{}']",
    },
    "desktop_rendered": "css: div.desktop.container.oneOne.oneAppLayoutHost[data-aura-rendered-by]",
    "loading_box": "css: div.auraLoadingBox.oneLoadingBox",
    "modal": {
        "button": "//div[contains(@class,'uiModal')]//div[contains(@class,'modal-footer')]//button[.//span[text()='{}']]",
        "close": "css: button.slds-modal__close",
        "error_messages": "css: div.pageLevelErrors ul.errorsList li",
        "fade_in": "css: div.slds-fade-in-open",
        "has_error": "css: div.pageLevelErrors",
        "is_open": "css: div.uiModal div.panel.slds-modal",
    },
    "object": {
        "button": "css: div.windowViewMode-normal ul.forceActionsContainer.oneActionsRibbon a[title='{}']",
        "field": "//div[contains(@class, 'uiInput')][.//label[contains(@class, 'uiLabel')][.//span[text()='{}']]]//input",
        "field_lookup_link": "//a[@role='option'][.//div[@title='{}']]",
        "field_lookup_value": "//div[contains(@class, 'uiInput')][.//label[contains(@class, 'uiLabel')][.//span[text()='{}']]]//span[contains(@class,'pillText')]",
        "record_type_option": "//div[contains(@class, 'changeRecordTypeOptionRightColumn')]//span[text()='{}']",
    },
    "record": {
        "header": {
            "field": "//li[contains(@class, 'slds-page-header__detail-block')][.//span[contains(@class, 'slds-form-element__label')][@title='{}']]",
            "field_value": "//li[contains(@class, 'slds-page-header__detail-block')][.//span[contains(@class, 'slds-form-element__label')][@title='{}']]//div[contains(@class, 'slds-form-element__static')]/span[text()]",
            "field_value_link": "//li[contains(@class, 'slds-page-header__detail-block')][.//span[contains(@class, 'slds-form-element__label')][@title='{}']]//div[contains(@class, 'slds-form-element__static')]//a",
            "field_value_checked": "//li[contains(@class, 'slds-page-header__detail-block')][.//span[contains(@class, 'slds-form-element__label')][@title='{}']]//span[contains(@class, 'uiOutputCheckbox')]//img[@alt='True']",
            "field_value_unchecked": "//li[contains(@class, 'slds-page-header__detail-block')][.//span[contains(@class, 'slds-form-element__label')][@title='{}']]//span[contains(@class, 'uiOutputCheckbox')]//img[@alt='False']",
        },
        "related": {
            "card": "//article[contains(@class, 'forceRelatedListCardDesktop')][.//img][.//span[@title='{}']]",
            "button": "//article[contains(@class, 'forceRelatedListCardDesktop')][.//img][.//span[@title='{}']]//a[@title='{}']",
            "count": "//article[contains(@class, 'forceRelatedListCardDesktop')][.//img]//span[@title='{}']/following-sibling::span",
            "link": "//article[contains(@class, 'forceRelatedListCardDesktop')][.//img][.//span[@title='{}']]//table[contains(@class,'forceRecordLayout')]/tbody/tr[.//th/div/a[contains(@class,'textUnderline')]][.//td/a[@title='{}']]/th//a",
            "popup_trigger": "//article[contains(@class, 'forceRelatedListCardDesktop')][.//img][.//span[@title='{}']]//tr[.//a[text()='{}']]//div[contains(@class, 'forceVirtualAction')]//a",
        },
    },
    "popup": {
        "link": "//div[contains(@class, 'uiPopupTarget')][contains(@class, 'visible')]//a[@title='{}']"
    },
    "spinner": "css: div.slds-spinner",
    "tabs": {"tab": ""},
    "actions": "css: ul.oneActionsRibbon",
    "body": "//div[contains(@class, 'slds-template__container')]/*",
}
