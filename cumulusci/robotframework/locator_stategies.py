"""
Custom locator strategies

We have a couple that live in Salesforce.robot which I hope to move here eventually
so that they are all in one place.
"""


class LocatorStrategies:
    def locate_element_by_label(self, browser, locator, tag, constraints):
        """Find a lightning component, input, or textarea based on a label

        If the component is inside a fieldset, the fieldset label can
        be prefixed to the label with a double colon in order to
        disambiguate the label.  (eg: Other address::First Name)


        If the label is inside nested ligntning components (eg:
        <lightning-input><lightning-combobox>), the component closest
        to the label will be returned.

        If a lightning component cannot be found for the label, an
        attempt will be made to find an input or textarea associated
        with the label.

        This is registered as a custom locator strategy named "label"

        Example:

        The following two lines produce identical results:

        | ${element}=  Locate element by label    Expected Delivery Date::Date
        | ${element}=  Get webelement             label:Expected Delivery Date::Date

        """

        if "::" in locator:
            fieldset, label = [x.strip() for x in locator.split("::", 1)]
            fieldset_prefix = f'//fieldset[.//*[.="{fieldset}"]]'
        else:
            label = locator
            fieldset_prefix = ""

        xpath = fieldset_prefix + (
            # a label with the given text, optionally with a leading
            # or trailing "*" (ie: required field)
            f'//label[.="{label}" or .="*{label}" or .="{label}*"]'
            # then find the nearest ancestor lightning component
            '/ancestor::*[starts-with(local-name(), "lightning-")][1]'
        )
        elements = browser.find_elements_by_xpath(xpath)

        if not elements:
            # fall back to finding an input or textarea based on the 'for'
            # attribute of a label
            xpath = fieldset_prefix + (
                "//*[self::input or self::textarea]"
                f'[@id=string(//label[.="{label}" or .="*{label}" or .="{label}*"]/@for)]'
            )
            elements = browser.find_elements_by_xpath(xpath)

        return elements
