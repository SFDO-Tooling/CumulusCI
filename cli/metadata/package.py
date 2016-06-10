# Inputs
# source: location of the source directory

# Initialize new package xml file

# Loop through subdirectories in package

    # Determine type

    # Select parser

    # Parse files to generate <types><members>NAME</members><name>TYPE</name></types>

        # Handle special cases
    
            # Reports (Report and report folder must be listed as members.  Reports are prefixed with FOLDER_NAME/)

    # Contains Subtypes?

        # Parse subtypes

import os
from xml.dom import minidom

class BaseMetadataParser(object):

    def __init__(self, metadata_type, directory):
        self.directory = directory
        self.members = []

    def __call__(self):
        self.parse_items()
        self.print_xml()

    def parse_items(self):
        # Loop through items
        for item in os.listdir(self.directory):
            self.parse_item(item)

    def parse_item(self, item):
        members = self._parse_item(item)
        if members:
            self.members.extend(members)

    def _parse_item(self, item):
        "Receives a file or directory name and returns a list of members"
        raise NotImplemented("Subclasses should implement their parser here")

    def print_xml(self):
        output = u'    <types>\n'
        for member in self.members:
            output += u'        <members>%{0}</members>\n'.format(member) 
        output += u'        <name>%{0}</name>\n'.format(self.metadata_type) 
        output += u'    </types>\n'
        

class MetadataFileNamesParser(BaseMetadataParser):
    
    def _parse_item(self, item):
        return ['.'.join(item.split('.')[:-1]),]

class MissingNameElementError(BaseException):
    pass

class MetadataXmlElementParser(BaseMetadataParser):

    def __init__(self, metadata_type, directory, item_element, name_element):
        super(MetadataXmlElementParser, self).__init__(metadata_type, directory)
        self.item_element = item_element
        self.name_element = name_element

    def _parse_item(self, item):
        dom = minidom.parse(self.directory + '/' + item)
        members = []

        for item in self.get_item_elements(dom):
            members.append(self.get_item_name(item))
       
    def get_item_elements(self, dom): 
        return dom.getElementsByTagName(self.item_element)

    def get_name_elements(self, item):
        return item.getElementsByTagName(self.name_element)

    def get_item_name(self, item):
        """ Returns the value of the first name element found inside of element """
        names = self.get_name_elements(item)
        if not names:
            raise MissingNameElementError

        return names[0].nodeValue

