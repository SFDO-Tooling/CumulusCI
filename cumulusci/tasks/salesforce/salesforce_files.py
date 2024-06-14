from cumulusci.tasks.salesforce import BaseSalesforceApiTask
import requests
import os
import json

class ListFiles(BaseSalesforceApiTask):
    task_docs = """
    Lists the available documents that has been uploaded to a library in Salesforce CRM Content or Salesforce Files
    """

    def _run_task(self):
        self.return_values = [
            {
                "Id": result["Id"],
                "FileName": result["Title"],
                "FileType": result["FileType"],
            }
            for result in self.sf.query(
                "SELECT Title, Id, FileType FROM ContentDocument"
            )["records"]
        ]
        self.logger.info(f"Found {len(self.return_values)} files")
        if len(self.return_values) > 0:
            self.logger.info(f"{'Id':<20} {'FileName':<50} {'FileType':<10}")

            # Print each row of the table
            for file_desc in self.return_values:
                self.logger.info(
                    f"{file_desc['Id']:<20} {file_desc['FileName']:<50} {file_desc['FileType']:<10}"
                )

        return self.return_values

class RetrieveFiles(BaseSalesforceApiTask):
    #task.org_config
    task_docs = """
    This task downloads all the documents (files) that have been uploaded to a library in Salesforce CRM Content or Salesforce Files. 
    Use the task display_files in order to view the files that are available to download.
    """
    task_options = {
        "output_directory": {
            "description": "The directory where the files will be saved. By default, files will be saved in Downloads",
            "required": False,
        },
         "file_id_list": {
            "description": "Specify a comma-separated list of Ids files to download. All the availables files are downloaded by default. Use display_files task to view files and their Ids",
            "required": False,
        },
    }
    
    def _init_options(self, kwargs):
        super(RetrieveFiles, self)._init_options(kwargs)

        if "output_directory" not in self.options:
            self.options["output_directory"] = "Files"
        
        if "file_id_list" not in self.options:
            self.options["file_id_list"] = ""

        self.return_values = []

    def _run_task(self):
        self.logger.info(f"Retrieving files from the specified org..")
        output_directory = self.options["output_directory"]
        self.logger.info(f"Output directory: {output_directory}")

        query_condition = ''

        file_id_list = self.options["file_id_list"]

        if file_id_list: # If the list of Ids of files to be downloaded is specify, fetch only those files.
            items_list = [f"'{item.strip()}'" for item in file_id_list.split(",")]  
            query_condition = f"AND ContentDocumentId IN ({','.join(items_list)})"

        available_files = [
            {
                "Id": result["Id"],
                "FileName": result["Title"],
                "FileType": result["FileType"],
                "VersionData": result["VersionData"],
                "ContentDocumentId": result["ContentDocumentId"]
            }
            for result in self.sf.query(
                f'SELECT Title, Id, FileType, VersionData, ContentDocumentId FROM ContentVersion WHERE isLatest=true {query_condition}'
            )["records"]
        ]

        self.logger.info(f"Found {len(available_files)} files in the org.\n")
        self.logger.info(f'Files will be downloaded in the directory: {self.options["output_directory"]} \n' )

        for current_file in available_files:
            versionData = current_file["VersionData"]
            url = f"{self.org_config.instance_url}/{versionData}"
            headers = {"Authorization": f"Bearer {self.org_config.access_token}"}

            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()

            file_extension = current_file["FileType"].lower()
            local_filename = f"{current_file['FileName']}.{file_extension}"
            local_filename = os.path.join(output_directory, local_filename)  

            self.logger.info(f"Downloading:   {current_file['FileName']}")

            file_exists = os.path.exists(local_filename)

            if file_exists:
                file_name = current_file['FileName']
                self.logger.info(f'A file with the name {file_name} already exists. in the directory. This file will be renamed.')
            if file_exists:
                count = 1
                while True:
                    local_filename = os.path.join(output_directory, f"{current_file['FileName']} ({count}).{file_extension}")
                    if not os.path.exists(local_filename):
                        break
                    count+=1
            
            os.makedirs(os.path.dirname(local_filename), exist_ok=True)  # Create the folder if it doesn't exist

            with open(local_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            self.logger.info('\n')

        self.return_values = available_files
        return self.return_values
    
class UploadFiles(BaseSalesforceApiTask):
    task_docs = """
    This task uploads files to a Salesforce org. 
    """
    task_options = {
        "path": {
            "description": "The directory to upload files from. By default, files under 'Files' folder are uploaded.",
            "required": False,
        },
        "file_list": {
            "description": "Specify a comma-separated list of files to upload. All the files in the specified directory are uploaded by default.",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        super(UploadFiles, self)._init_options(kwargs)

        if "path" not in self.options:
            self.options["path"] = "Files"
        
        if "file_list" not in self.options:
            self.options["file_list"] = ""
        
        self.return_values = []

    def _run_task(self):
        path = self.options["path"]
        file_list = self.options["file_list"]

        # Salesforce REST API endpoint for uploading files
        api_version = self.project_config.project__package__api_version
        url = f"{self.org_config.instance_url}/services/data/v{api_version}/sobjects/ContentVersion/"

        # Prepare the request headers
        headers = {
            "Authorization": f"Bearer {self.org_config.access_token}",
        }

        if file_list:
            files_to_upload = file_list.split(',')
        else:
            files_to_upload = os.listdir(path)

        for filename in files_to_upload:
            file_path = os.path.join(path, filename.strip())

            if os.path.isfile(file_path):
                with open(file_path, 'rb') as file:
                    # Construct the payload for the entity content
                    title = os.path.splitext(os.path.basename(file_path))[0] # File name

                    entity_content = {
                        'Title': title,
                        'PathOnClient': file_path,
                    }

                    self.return_values.append(entity_content)

                    files = {
                        'entity_content': ('', json.dumps(entity_content), 'application/json'),
                        'VersionData': (filename, file, 'application/octet-stream')
                    }

                    try:
                        response = requests.post(url, headers=headers, files=files)
                        response.raise_for_status()  # Raise an exception for HTTP errors

                        # Parse the response JSON
                        response_json = response.json()

                        if response.status_code == 201: # Upload successful
                            content_version_id = response_json["id"]
                            self.logger.info(f"File '{filename}' uploaded successfully. ContentVersion Id: {content_version_id}")
                        else:
                            self.logger.error(f"Failed to upload file '{filename}': {response_json}")
                    except requests.RequestException as e:
                        self.logger.error(f"Error uploading file '{filename}': {e}")
                        self.logger.error(e.response.content)  # Print response content in case of error
        
        return self.return_values # Returns a list containing all the files uplaoded.