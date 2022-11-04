lex_locators = {
    "actions": "//runtime_platform_actions-actions-ribbon//ul|//ul[contains(concat(' "
    "',normalize-space(@class),' '),' oneActionsRibbon ')]",
    "app_launcher": {
        "app_link": "//one-app-launcher-modal//one-app-launcher-app-tile//a[.='{}']",
        "button": "//div[contains(@class,'appLauncher')]//button[//div[contains(@class,'slds-icon-waffle')]]",
        "current_app": "//div[contains(@class,'navLeft')]//span[contains(@class,'appName')]/span[text()='{}']",
        "menu": "//div[contains(@class, 'appLauncherMenu')]",
        "tab_link": "//one-app-launcher-modal//one-app-launcher-tab-item//a[.='{}']",
        "view_all": "//div[contains(@class, "
        "'appLauncherMenu')]//button[text()='View "
        "All']",
    },
    "body": "//div[contains(@class, 'slds-template__container')]/*",
    "desktop_rendered": "css: "
    "div.desktop.container.oneOne.oneAppLayoutHost[data-aura-rendered-by]",
    "list_view_menu": {
        "button": "css:button[title='List View Controls']",
        "item": "//div[@title='List View " "Controls']//ul[@role='menu']//li/a[.='{}']",
    },
    "loading_box": "css: div.auraLoadingBox.oneLoadingBox",
    "modal": {
        "button": "//div[contains(@class,'uiModal')]//button[.='{}']",
        "close": "css: button.slds-modal__close",
        "error_messages": "css: div.pageLevelErrors ul.errorsList li",
        "fade_in": "css: div.slds-fade-in-open",
        "field_alert": "//div[contains(@class, 'forceFormPageError')]",
        "has_error": "css: div.forceFormPageError",
        "is_open": "css: div.uiModal div.panel.slds-modal",
        "review_alert": "//a[@records-recordediterror_recordediterror "
        "and text()='{}']",
    },
    "object": {
        "button": "//div[contains(@class, "
        "'slds-page-header')]//*[self::a[@title='{title}'] "
        "or self::button[@name='{title}']]",
        "field": "//lightning-input[.//label[text()='{}']]//input",
        "field_label": "//label[@for!='' and "
        "text()='{}']|//label[@for!=''][./span[text()='{}']]",
        "field_lookup_link": "//*[@role='option'][.//*[@title='{}']]",
        "field_lookup_value": "//div[contains(@class, "
        "'uiInput')][.//label[contains(@class, "
        "'uiLabel')][.//span[text()='{}']]]//span[contains(@class,'pillText')]",
        "record_type_option": "//div[contains(@class, "
        "'changeRecordTypeOptionRightColumn')]//span[text()='{}']",
    },
    "object_list": {
        "checkbutton": '//tbody/tr[.//*[text()="{}"]]//td[.//input[@type="checkbox"]]',
        "status_info": "//force-list-view-manager-status-info",
    },
    "popup": {
        "link": "//div[contains(@class, "
        "'uiPopupTarget')][contains(@class, "
        "'visible')]//a[@title='{}']"
    },
    "record": {
        "header": {
            "field": "//li[contains(@class, "
            "'slds-page-header__detail-block')][.//span[contains(@class, "
            "'slds-form-element__label')][@title='{}']]",
            "field_value": "//records-lwc-highlights-panel//records-highlights-details-item[.//*[contains(@class, "
            "'slds-text-title') and "
            "text()='{}']]//p[contains(@class, "
            "'fieldComponent')]//*[text()]",
            "field_value_checked": "//li[contains(@class, "
            "'slds-page-header__detail-block')][.//span[contains(@class, "
            "'slds-form-element__label')][@title='{}']]//span[contains(@class, "
            "'uiOutputCheckbox')]//img[@alt='True']",
            "field_value_link": "//records-lwc-highlights-panel//records-highlights-details-item[.//*[.='{}']]//a",
            "field_value_unchecked": "//li[contains(@class, "
            "'slds-page-header__detail-block')][.//span[contains(@class, "
            "'slds-form-element__label')][@title='{}']]//span[contains(@class, "
            "'uiOutputCheckbox')]//img[@alt='False']",
        },
        "related": {
            "button": "//*[@data-component-id='force_relatedListContainer']//article[contains(@class, "
            "'slds-card "
            "slds-card_boundary')][.//span[@title='{}']]//*[text()='{}']",
            "card": "//*[@data-component-id='force_relatedListContainer']//article[.//span[@title='{}']]",
            "count": "//*[@data-component-id='force_relatedListContainer']//article//span[@title='{}']/following-sibling::span",
            "link": "//*[@data-component-id='force_relatedListContainer']//article[.//span[@title='{}']]//*[text()='{}']",
            "popup_trigger": "//*[@data-component-id='force_relatedListContainer']//article[.//span[@title='{}']]//span[text()='Show "
            "Actions']",
        },
    },
    "spinner": "css: div.slds-spinner",
    "tabs": {"tab": ""},
}
