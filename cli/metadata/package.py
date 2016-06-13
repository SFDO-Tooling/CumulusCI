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
import xml.etree.ElementTree as ET
import yaml

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

class MetadataParserMissingError(Exception):
    pass

class PackageXmlGenerator(object):
    def __init__(self, directory, api_version, package_name=None, install_class=None, uninstall_class=None):
        f_metadata_map = open(__location__ + '/metadata_map.yml', 'r')
        self.metadata_map = yaml.load(f_metadata_map)
        self.directory = directory
        self.types = []

    def __call__(self):
        self.parse_types()
        self.print_xml()

    def parse_types(self):
        for item in os.listdir(self.directory):
            if item == 'package.xml':
                continue
            if item.startswith('.'):
                continue
            import pdb; pdb.set_trace()
            parser_config = self.metadata_map.get(item)
            if not parser_config:
                raise MetadataParserMissingError


            # Construct the parser
            parser = globals()[parser_config['class']](
                parser_config['type'],                # Metadata Type
                self.directory + '/' + item,          # Directory
                parser_config.get('extension', ''),   # Extension
                #*parser_config.get('args', [])       # Extra args
                #**parser_config.get('kwargs', {})     # Extra kwargs
            )

            # Run the parser
            self.types.append(parser)

    def print_xml(self):
        for parser in self.types:
            parser()
        

class BaseMetadataParser(object):

    def __init__(self, metadata_type, directory, extension):
        self.metadata_type = metadata_type
        self.directory = directory
        self.extension = extension
        self.members = []

    def __call__(self):
        self.parse_items()
        self.print_xml()

    def parse_items(self):
        # Loop through items
        for item in os.listdir(self.directory):
            if self.extension and not item.endswith('.' + self.extension):
                continue
            
            self.parse_item(item)

    def parse_item(self, item):
        members = self._parse_item(item)
        if members:
            self.members.extend(members)

    def _parse_item(self, item):
        "Receives a file or directory name and returns a list of members"
        raise NotImplemented("Subclasses should implement their parser here")

    def strip_extension(self, filename):
        return '.'.join(filename.split('.')[:-1])

    def print_xml(self):
        output = u'    <types>\n'
        for member in self.members:
            output += u'        <members>{0}</members>\n'.format(member) 
        output += u'        <name>{0}</name>\n'.format(self.metadata_type) 
        output += u'    </types>\n'
        print output
        

class MetadataFilenameParser(BaseMetadataParser):
    
    def _parse_item(self, item):
        return [self.strip_extension(item),]

class MissingNameElementError(Exception):
    pass

class MetadataXmlElementParser(BaseMetadataParser):

    namespaces = {'sf': 'http://soap.sforce.com/2006/04/metadata'}

    def __init__(self, metadata_type, directory, extension, item_xpath, name_xpath=None):
        super(MetadataXmlElementParser, self).__init__(metadata_type, directory, extension)
        self.item_xpath = item_xpath
        if not name_xpath:
            name_xpath = './sf:fullName'
        self.name_xpath = name_xpath

    def _parse_item(self, item):
        root = ET.parse(self.directory + '/' + item)
        members = []

        parent = self.strip_extension(item)

        for item in self.get_item_elements(root):
            members.append(self.get_item_name(item, parent))

        return members
       
    def get_item_elements(self, root): 
        return root.findall(self.item_xpath, self.namespaces)

    def get_name_elements(self, item):
        return item.findall(self.name_xpath, self.namespaces)

    def get_item_name(self, item, parent):
        """ Returns the value of the first name element found inside of element """
        names = self.get_name_elements(item)
        if not names:
            raise MissingNameElementError

        name = names[0].text
        prefix = self.item_name_prefix(parent)
        if prefix:
            name = prefix + name
            
        return name

    def item_name_prefix(self, parent):
        return parent + '.'
