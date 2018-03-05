
selectors = {
    'app_launcher': {
        'app_link': "//div[@class='slds-section slds-is-open salesforceIdentityAppLauncherDesktopInternal']//section[@id='cards']//div[@class='appTileTitle' and text()='{}']",
        'button': "css: nav.appLauncher button div.slds-icon-waffle",
        'current_app': "//div[contains(@class,'navLeft')]//span[contains(@class,'appName')]/span[text()='{}']",
        'tab_link': "css: a.app-launcher-link[title='{}']",
    },
    'modal': {
        'is_open': "css: div.DESKTOP.uiModal.forceModal.open.active",
        'button': "css: div.uiModal div.forceModalActionContainer button[title='{}']",
    },
    'object': {
        'button': "css: ul.forceActionsContainer.oneActionsRibbon a[title='{}']",
        'field': "//div[contains(@class, 'uiInput')][.//label[contains(@class, 'uiLabel')][.//span[text()='{}']]]//input"
    },
    'tabs': {
        'tab': '',
    },
}
