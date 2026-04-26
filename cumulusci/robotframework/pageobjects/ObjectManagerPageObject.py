from selenium.webdriver.common.keys import Keys

from cumulusci.robotframework.pageobjects import BasePage, pageobject
from cumulusci.robotframework.utils import capture_screenshot_on_error

object_manager = {
    "button": "//input[@title='{}']",
    "input": "//input[@id='{}']",
    "select_related": "//select[@id = '{}']",
    "select_related_option": "//select[@id = 'DomainEnumOrId']/option[@value='{}']",
    "search_result": "//section[@class='related-list-card']//a[.=\"{}\"]",
    "formula_txtarea": "//textarea[@id = '{}']",
    "object_result": "//th/a[text()='{}']",
    "link-text": "//a[contains(text(),'{}')]",
    "button-with-text": "//button[contains(text(),'{}')]",
    "frame_new": "//iframe[contains(@name, '{}') or contains(@title, '{}')]",
    "action_menu": "//tr[.//a[.='{}']]//div[contains(@class, 'objectManagerVirtualActionMenu')]//a",
    "action_menu_item": "//div[@class='actionMenu']//a[@role='menuitem' and .='{}']",
    "delete_confirm_btn": "//button[contains(@class,'forceActionButton')]",
}
# All common elements
search_button = object_manager["input"].format("globalQuickfind")
currency_locator = object_manager["input"].format("dtypeC")
next_button = object_manager["button"].format("Next")
save_button = object_manager["button"].format("Save")
text_locator = object_manager["input"].format("dtypeS")
formula_locator = object_manager["input"].format("dtypeZ")
checkbox_option = object_manager["input"].format("fdtypeB")
formula_txtarea = object_manager["formula_txtarea"].format("CalculatedFormula")
check_syntax = object_manager["button"].format("Check Syntax")
actions_menu = object_manager["action_menu"]
action_item_delete = object_manager["action_menu_item"].format("Delete")
confirm_delete = object_manager["delete_confirm_btn"]
lookup_locator = object_manager["input"].format("dtypeY")


@pageobject(page_type="ObjectManager")
class ObjectManagerPage(BasePage):
    """A page object representing the Object Manager of an object.
    Example
    | Go to page   ObjectManager  Contact
    """

    def _go_to_page(self):
        url_template = "{root}/lightning/setup/ObjectManager/home"
        url = url_template.format(root=self.cumulusci.org.lightning_base_url)
        self.selenium.go_to(url)
        object_name = self.object_name
        self.salesforce.wait_until_loading_is_complete()
        self.selenium.wait_until_page_contains_element(search_button)
        self.selenium.press_keys(search_button, object_name, "RETURN")
        object_locator = object_manager["object_result"].format(object_name)
        self.selenium.wait_until_element_is_visible(object_locator)
        self.salesforce._jsclick(object_locator)
        self.selenium.wait_until_location_contains("Details/view", timeout=90)

    def _is_current_page(self):
        self.selenium.location_should_contain("Details/view")

    @capture_screenshot_on_error
    def switch_tab_to(self, tab):
        """Clicks on the name of the tab specified and sets the page view to be on the tab specified
        Example
        | Switch Tab To     Fields & Relationships
        """
        leftnavoption = object_manager["link-text"].format(tab)
        self.selenium.click_element(leftnavoption)

    def _is_current_tab(self, tab):
        tab_view = f"{tab}/view"
        self.selenium.location_should_contain(tab_view)

    @capture_screenshot_on_error
    def create_currency_field(self, field_name):
        """Creates a currency field by taking in the field name"""
        self.selenium.wait_until_page_contains_element(currency_locator, timeout=60)
        self.selenium.click_element(currency_locator)
        self.selenium.wait_until_page_contains_element(next_button, 60)
        self.selenium.click_element(next_button)
        self.salesforce.populate_field("Field Label", field_name)
        self.salesforce.populate_field("Length", "16")
        self.salesforce.populate_field("Decimal Places", "2")
        self.salesforce.populate_field(
            "Description", "This is a custom field generated during automation"
        )
        self.selenium.click_element(next_button)
        self.selenium.click_element(next_button)
        self.selenium.click_element(save_button)
        self.selenium.wait_until_location_contains(
            "FieldsAndRelationships/view",
            timeout=90,
            message="Fields And Relationships page did not load in 1 min",
        )

    @capture_screenshot_on_error
    def create_text_field(self, field_name):
        """Creates a text field by taking in the field name"""
        self.selenium.wait_until_page_contains_element(text_locator, timeout=60)
        self.selenium.click_element(text_locator)
        self.selenium.click_element(next_button)
        self.salesforce.populate_field("Field Label", field_name)
        self.salesforce.populate_field("Length", "255")
        self.salesforce.populate_field(
            "Description", "This is a custom field generated during automation"
        )
        self.selenium.click_element(next_button)
        self.selenium.click_element(next_button)
        self.selenium.click_element(save_button)
        self.selenium.wait_until_location_contains(
            "FieldsAndRelationships/view",
            timeout=90,
            message="Fields And Relationships page did not load in 1 min",
        )

    @capture_screenshot_on_error
    def create_formula_field(self, field_name, formula):
        """Creates a formula field by providing the field_name, formula and forumla fields"""
        self.selenium.wait_until_page_contains_element(formula_locator, 60)
        self.selenium.click_element(formula_locator)
        self.selenium.wait_until_page_contains_element(next_button, 60)
        self.selenium.click_element(next_button)
        self.salesforce.populate_field("Field Label", field_name)
        self.selenium.wait_until_page_contains_element(checkbox_option, 60)
        self.selenium.click_element(checkbox_option)
        self.selenium.click_element(next_button)
        self.selenium.wait_until_page_contains_element(formula_txtarea, 60)
        self.selenium.get_webelement(formula_txtarea).send_keys(formula)
        self.selenium.click_element(check_syntax)
        self.selenium.click_element(next_button)
        self.selenium.click_element(next_button)
        self.selenium.click_element(save_button)
        self.selenium.wait_until_location_contains(
            "FieldsAndRelationships/view",
            timeout=90,
            message="Detail page did not load in 1 min",
        )

    def create_lookup_field(self, field_name, related):
        """Creates a Lookup field by taking in the inputs field_name and related field"""
        option = object_manager["select_related_option"].format(related)
        related = object_manager["select_related"].format("DomainEnumOrId")
        self.selenium.wait_until_page_contains_element(lookup_locator, 60)
        self.selenium.click_element(lookup_locator)
        self.selenium.wait_until_page_contains_element(next_button, 60)
        self.selenium.click_element(next_button)
        self.selenium.wait_until_page_contains_element(related, 60)
        self.salesforce.scroll_element_into_view(related)
        self.selenium.get_webelement(related).click()
        self.selenium.click_element(option)
        self.selenium.wait_until_page_contains_element(next_button, 60)
        self.selenium.click_element(next_button)
        self.salesforce.populate_field("Field Label", field_name)
        self.salesforce.populate_field(
            "Description", "This is a custom field generated during automation"
        )
        self.selenium.click_element(next_button)
        self.selenium.click_element(next_button)
        self.selenium.click_element(next_button)
        self.selenium.click_element(save_button)
        self.selenium.wait_until_location_contains(
            "FieldsAndRelationships/view",
            timeout=90,
            message="Detail page did not load in 1 min",
        )

    @capture_screenshot_on_error
    def is_field_present(self, field_name):
        """Searches for the field name (field_name) and asserts the field got created"""
        self.selenium.wait_until_page_contains_element(search_button)
        self.selenium.clear_element_text(search_button)
        self.selenium.press_keys(search_button, field_name, "ENTER")
        self.selenium.wait_until_element_is_not_visible("sf:spinner")
        search_results = object_manager["search_result"].format(field_name)
        self.selenium.wait_until_page_contains_element(search_results)

    @capture_screenshot_on_error
    def delete_custom_field(self, field_name):
        """Searches for the custom field and performs the delete action from the actions menu next to the field"""
        action_menu_button = actions_menu.format(field_name)
        self.is_field_present(field_name)

        self.selenium.wait_until_page_contains_element(action_menu_button)
        self.salesforce.scroll_element_into_view(action_menu_button)

        # I don't know why, but sometimes clicking the action menu just
        # doesn't work. The menu doesn't appear, or clicking the item on
        # the menu does nothing. So, we'll try and handful of times.
        # Yes, this feels icky.
        for tries in range(5):
            try:
                self.selenium.wait_until_element_is_visible(action_menu_button)
                self.selenium.click_element(action_menu_button)
                self.selenium.wait_until_element_is_visible(
                    action_item_delete, timeout="5 seconds"
                )
                self.selenium.click_element(action_item_delete, action_chain=True)
                self.selenium.wait_until_element_is_visible(
                    confirm_delete, timeout="5 seconds"
                )
                self.selenium.click_element(confirm_delete, action_chain=True)
                self.selenium.wait_until_location_contains("/view", timeout=90)
                return

            except Exception as e:
                self.builtin.log(
                    f"on try #{tries + 1} we caught this error: {e}", "DEBUG"
                )
                self.builtin.sleep("1 second")
                last_error = e
        raise (last_error)

    @capture_screenshot_on_error
    def create_custom_field(self, **kwargs):
        """creates a custom field if one doesn't already exist by the given name (Field_Name)
        |  Example
        | Create custom field
        | ...  Object=Payment
        | ...  Field_Type=Formula
        | ...  Field_Name=Is Opportunity From Prior Year
        | ...  Formula=YEAR( npe01__Opportunity__r.CloseDate ) < YEAR( npe01__Payment_Date__c )
        """
        self.selenium.wait_until_page_contains_element(search_button, 60)
        self.selenium.get_webelement(search_button).send_keys(kwargs["Field_Name"])
        self.selenium.get_webelement(search_button).send_keys(Keys.ENTER)
        self.salesforce.wait_until_loading_is_complete()
        search_results = object_manager["search_result"].format(kwargs["Field_Name"])
        count = len(self.selenium.get_webelements(search_results))
        if count != 1:
            locator = object_manager["button-with-text"].format("New")
            self.selenium.wait_until_page_contains_element(locator, 60)
            self.selenium.get_webelement(locator).click()
            self.salesforce.wait_until_loading_is_complete()
            framelocator = object_manager["frame_new"].format("vfFrameId", "vfFrameId")
            self.selenium.wait_until_element_is_visible(framelocator, timeout=60)
            frame = self.selenium.get_webelement(framelocator)
            self.selenium.select_frame(frame)
            type = kwargs["Field_Type"]
            if type.lower() == "lookup":
                self.create_lookup_field(kwargs["Field_Name"], kwargs["Related_To"])
            elif type.lower() == "currency":
                self.create_currency_field(kwargs["Field_Name"])
            elif type.lower() == "formula":
                self.create_formula_field(kwargs["Field_Name"], kwargs["Formula"])
            elif type.lower() == "text":
                self.create_text_field(kwargs["Field_Name"])
            self.selenium.unselect_frame()
