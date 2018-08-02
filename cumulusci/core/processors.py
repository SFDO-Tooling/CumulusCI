
import io
import os
import base64
import zipfile
import tempfile

class MetadataProcessor(object):
    """
    MetadataProcessor allows a caller (task) to:
    - walk a metadata tree (presumably on the filesystem)
    - process each item (for example to remove a version dependency) with pre-registered processors
    - get back a zipfile ready for the salesforce metadata api
    """
    def __init__(self, path):
        self.path = path
        self.processors = []

        self._stream = io.BytesIO()

    def process(self):
        zipf = zipfile.ZipFile(self._stream, 'w', zipfile.ZIP_DEFLATED)

        # by not chdiring here first, the roots aren't relative... need to sort that out
        for root, dirs, files in os.walk(self.path):
            
            for fname in files:
                
                fpath = os.path.join(root, fname)
                
                #fp = open(fpath, 'r')

                # get the file name relative to the root
                # read file in
                # run through processors in order, one value into next
                # write result into zipfile.


                # todo: processors run here
                for processor in self.processors:
                    processor(fpath)
                zipf.writestr(fpath, )
        
        zipf.close() # actually compress the zipfile

    @property
    def base64_zip(self):
        self._stream.seek(0)
        return base64.b64encode(self._stream.read())
    

def noop_parser(mdapitype, filename, metadata, body=None):
    return mdapitype, filename, metadata, body
