"""
This class is used by test_pageobjects
"""
from cumulusci.robotframework.pageobjects import ListingPage, pageobject


# The point of this class is to test out using an alias
@pageobject(page_type="Listing", object_name="Custom Object")
class CustomObjectListingPage(ListingPage):
    _object_name = "CustomObject__c"
