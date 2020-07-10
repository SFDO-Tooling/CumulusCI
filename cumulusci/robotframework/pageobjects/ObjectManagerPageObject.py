import time
from cumulusci.robotframework.utils import capture_screenshot_on_error
from cumulusci.robotframework.pageobjects import BasePage
from cumulusci.robotframework.pageobjects import pageobject
from selenium.webdriver.common.keys import Keys

object_manager = {"button":"//input[@title='{}']",
				  "input":"//input[@id='{}']",
				  "select_related":"//select[@id = '{}']",
				  "select_related_option":"//select[@id = 'DomainEnumOrId']/option[@value='{}']",
				  "search_result": "//tbody/tr/td/a/span[contains(text(),'{}')]",
				  "formula_txtarea": "//textarea[@id = '{}']",
				  "object_result": "//th/a[text()='{}']",
				  "link-text":"//a[contains(text(),'{}')]",
				  "button-with-text":"//button[contains(text(),'{}')]",
				  "frame_new":"//iframe[contains(@name, '{}') or contains(@title, '{}')]"
				  }

@pageobject(page_type="ObjectManager")
class ObjectManagerPage(BasePage):
    """A page object representing the Object Manager of an object.
	Example
	| Go to page   ObjectManager  Contact
	"""

    def _go_to_page(self):
        url_template = "{root}/lightning/setup/ObjectManager/home"
        url = url_template.format(
            root=self.cumulusci.org.lightning_base_url, object_name=self.object_name
        )
        self.selenium.go_to(url)
        search_button = object_manager["input"].format("globalQuickfind")
        object_name = self.object_name
        self.salesforce.wait_until_loading_is_complete()
        self.selenium.wait_until_page_contains_element(search_button)
        self.selenium.get_webelement(search_button).send_keys(object_name)
        self.selenium.get_webelement(search_button).send_keys(Keys.ENTER)
        object = object_manager["object_result"].format(object_name)
        self.selenium.wait_until_page_contains_element(object)
        self.selenium.click_element(object)
        self.selenium.wait_until_location_contains("Details/view", timeout=90)
        

	def _is_current_page(self):
		self.selenium.location_should_contain(
		"Detail/view"
		)
	
	@capture_screenshot_on_error
	def _switch_tab_to(self,tab):
		leftnavoption = object_manager["link-text"].format(tab)
		self.selenium.click_element(leftnavoption)

	def _is_current_tab(self,tab):
		self.selenium.location_should_contain(
			"Detail/view"
		)


    @capture_screenshot_on_error
    def create_currency_field(self, field_name):
        """Creates a currency field by taking in the field name"""
        currency_locator = object_manager["input"].format("dtypeC")
        next_button = object_manager["button"].format("Next")
        save_button = object_manager["button"].format("Save")
        self.selenium.wait_until_page_contains_element(currency_locator, timeout=60)
        self.selenium.click_element(currency_locator)
        time.sleep(1)
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
    def create_formula_field(self, field_name, formula):
        """ Creates a formula field by providing the field_name, formula and forumla fields"""
        formula_locator = object_manager["input"].format("dtypeZ")
        next_button = object_manager["button"].format("Next")
        save_button = object_manager["button"].format("Save")
        checkbox_option = object_manager["input"].format("fdtypeB")
        formula_txtarea = object_manager["formula_txtarea"].format("CalculatedFormula")
        check_syntax = object_manager["button"].format("Check Syntax")
        self.selenium.wait_until_page_contains_element(formula_locator, 60)
        self.selenium.click_element(formula_locator)
        time.sleep(1)
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
        """Creates a Lookpup field by taking in the inputs field_name and related field"""
        lookup_locator = object_manager["input"].format("dtypeY")
        next_button = object_manager["button"].format("Next")
        save_button = object_manager["button"].format("Save")
        option = object_manager["select_related_option"].format(related)
        related = object_manager["select_related"].format("DomainEnumOrId")
        self.selenium.wait_until_page_contains_element(lookup_locator, 60)
        self.selenium.click_element(lookup_locator)
        time.sleep(1)
        self.selenium.click_element(next_button)
        self.selenium.wait_until_page_contains_element(related, 60)
        self.selenium.scroll_element_into_view(related)
        self.selenium.get_webelement(related).click()
        self.selenium.click_element(option)
        time.sleep(2)
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
    def create_custom_field(self, **kwargs):
        """Ensure that the custom field does not exist prior and Creates a custom field based          on type paramenter and the field_name if the custom field exists it will not create the         custom field and exits out of object manager"""
        search_button = object_manager["input"].format("globalQuickfind")
        self.selenium.wait_until_page_contains_element(search_button, 60)
        self.selenium.get_webelement(search_button).send_keys(kwargs["Field_Name"])
        self.selenium.get_webelement(search_button).send_keys(Keys.ENTER)
        time.sleep(1)
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
