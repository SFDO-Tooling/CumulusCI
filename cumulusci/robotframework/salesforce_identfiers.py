

app_launcher_button = "css: nav.appLauncher button.salesforceIdentityAppLauncherHeader"
        self.selenium.click_button(identifier)

# Requires app_name
app_launcher_app_link = "//div[@class='slds-section slds-is-open salesforceIdentityAppLauncherDesktopInternal']//section[@id='cards']//a[//div[@class='appTileTitle' and text()='{}']]"
