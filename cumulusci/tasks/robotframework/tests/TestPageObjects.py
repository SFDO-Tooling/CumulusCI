from cumulusci.robotframework.pageobjects import pageobject, ListingPage, DetailPage


@pageobject(page_type="Listing", object_name="Something__c")
class SomethingListingPage(ListingPage):
    """Description of SomethingListingPage"""

    def keyword_one(self):
        pass

    def keyword_two(self):
        pass


@pageobject(page_type="Detail", object_name="Something__c")
class SomethingDetailPage(DetailPage):
    """Description of SomethingDetailPage"""

    def keyword_one(self):
        pass

    def keyword_two(self):
        pass

    def keyword_three(self):
        pass
