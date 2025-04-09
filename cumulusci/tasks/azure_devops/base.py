from datetime import datetime

from cumulusci.core.tasks import BaseTask
import cumulusci.core.azure_devops as scm #import get_azure_api_for_repo

class BaseAzureTask(BaseTask):
    def _init_task(self):
        super()._init_task()

        # Set azure variables
        self.azure_config = self.project_config.keychain.get_service("azure_devops")
        self.azure_connection = scm.get_azure_api_conntection( self.azure_config )
        self.azure_core_client = self.azure_connection.clients.get_core_client()

    def get_git_client(self):
        # Return azure repo
        self.git_client = self.azure_connection.clients.get_git_client()
    
    def get_tag_by_name(self):
        refs = self.git_client.get_refs(self.repo.id,self.repo.project.id,filter=f"tags/{self.options["src_tag"]}")
        if len(refs) == 1:
            return refs[0]
        
    def create_tag(self):
        src_tag_name = self.options["src_tag"]
        self.get_git_client()
        
        #TODO: Identify the repo name and project name of Azure.
        self.repo = self.git_client.get_repository(self.project_config.repo_name, self.project_config.repo_name)
        
        src_tag = self.get_tag_by_name()
        
        tag = None
        
        if src_tag is not None:
            #TODO: Need to find better way to import
            from azure.devops.v7_0.git.models import GitAnnotatedTag, GitObject
            clone_tag = GitAnnotatedTag()
            clone_tag.message = f"Cloned from {src_tag_name}"
            clone_tag.name = self.options["tag"]
            
            clone_tag.tagged_object = GitObject()
            clone_tag.tagged_object.object_id = src_tag.object_id
        
            tag = self.git_client.create_annotated_tag(clone_tag, self.repo.project.id, self.repo.id)
    
        return tag