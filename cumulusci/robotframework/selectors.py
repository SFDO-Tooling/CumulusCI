
selectors = {
    'app_launcher': {
        'button': "css: nav.appLauncher button.salesforceIdentityAppLauncherHeader",
        'app_link': "//div[@class='slds-section slds-is-open salesforceIdentityAppLauncherDesktopInternal']//section[@id='cards']//a[//div[@class='appTileTitle' and text()='{}']]",
        'tab_link': "css: a.app-launcher-link[title='{}']",
    },
    'tabs': {
        'tab': '',
    }
}
