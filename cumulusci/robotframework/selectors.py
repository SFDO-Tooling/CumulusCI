
selectors = {
    'app_launcher': {
        'app_link': "//div[@class='slds-section slds-is-open salesforceIdentityAppLauncherDesktopInternal']//section[@id='cards']//div[@class='appTileTitle' and text()='{}']",
        'button': "css: nav.appLauncher button div.slds-icon-waffle",
        'current_app': "//div[contains(@class,'navLeft')]//span[contains(@class,'appName')]/span[text()='{}']",
        'tab_link': "css: a.app-launcher-link[title='{}']",
    },
    'lex': {
        'modal': "css: div.DESKTOP.uiModal.forceModal.open.active",
    },
    'object': {
        'button': "css: ul.forceActionsContainer.oneActionsRibbon a[title='New']",
    },
    'tabs': {
        'tab': '',
    },
}
