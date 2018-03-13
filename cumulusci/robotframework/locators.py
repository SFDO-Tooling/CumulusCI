
lex_locators = {
    'app_launcher': {
        'app_link': "//div[@class='slds-section slds-is-open salesforceIdentityAppLauncherDesktopInternal']//section[@id='cards']//div[@class='appTileTitle' and text()='{}']",
        'button': "css: nav.appLauncher button div.slds-icon-waffle",
        'current_app': "//div[contains(@class,'navLeft')]//span[contains(@class,'appName')]/span[text()='{}']",
        'tab_link': "css: a.app-launcher-link[title='{}']",
    },
    'desktop_rendered': 'css: div.desktop.container.oneOne.oneAppLayoutHost[data-aura-rendered-by]',
    'loading_box': 'css: div.auraLoadingBox.oneLoadingBox',
    'modal': {
        'is_open': "css: div.DESKTOP.uiModal.forceModal.open.active",
        'button': "css: div.uiModal div.modal-footer button[title='{}']",
        'has_error': "css: div.pageLevelErrors",
        'error_messages': "css: div.pageLevelErrors ul.errorsList li",
    },
    'object': {
        'button': "css: div.windowViewMode-normal ul.forceActionsContainer.oneActionsRibbon a[title='{}']",
        'field': "//div[contains(@class, 'uiInput')][.//label[contains(@class, 'uiLabel')][.//span[text()='{}']]]//input",
        'field_lookup_value': "//a[@role='option'][.//div[@title='{}']]",
        'record_type_option': "//div[contains(@class, 'changeRecordTypeOptionRightColumn')]//span[text()='{}']",
    },
    'record': {
        'header': {
            'field': "//li[contains(@class, 'slds-page-header__detail')][.//p[contains(@class, 'slds-text-heading--label')][@title='{}']",
            'field_value': "//li[contains(@class, 'slds-page-header__detail')][.//p[contains(@class, 'slds-text-heading--label')][@title='{}']//span[contains(@class, 'uiOutput')][text()]",
            'field_value_link': "//li[contains(@class, 'slds-page-header__detail')][.//p[contains(@class, 'slds-text-heading--label')][@title='{}']]//a",
            'field_value_checked': "//li[contains(@class, 'slds-page-header__detail')][.//p[contains(@class, 'slds-text-heading--label')][@title='{}']]//span[contains(@class, 'uiOutputCheckbox')]//img[@alt='True']",
            'field_value_unchecked': "//li[contains(@class, 'slds-page-header__detail')][.//p[contains(@class, 'slds-text-heading--label')][@title='{}']]//span[contains(@class, 'uiOutputCheckbox')]//img[@alt='False']",
        },
        'related': {
            'button': "//article[contains(@class, 'forceRelatedListCardDesktop')][.//img][.//span[@title='{}']]//a[@title='{}']",
            'count': "//article[contains(@class, 'forceRelatedListCardDesktop')][.//img]//span[@title='{}']/following-sibling::span",
        },
    },
    'spinner': 'css: div.slds-spinner',
    'tabs': {
        'tab': '',
    },
}
