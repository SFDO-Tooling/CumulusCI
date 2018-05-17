from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class SOQLQuery(BaseSalesforceApiTask):
    name = 'SOQLQuery'

    task_options = {
        'object' : {'required':True, 'description':'The object to query'},
        'query' : {'required':True, 'description':'A valid bulk SOQL query for the object'},
        'result_file' : {'required':True,'description':'The name of the csv file to write the results to'}
    }

    def _run_task(self):
        self.logger.info('Creating bulk job for: {object}'.format(**self.options))
        job = self.bulk.create_query_job(self.options['object'], contentType='CSV')
        self.logger.info('Job id: {0}'.format(job))
        self.logger.info('Submitting query: {query}'.format(**self.options))
        batch = self.bulk.query(job,self.options['query'])
        self.logger.info('Batch id: {0}'.format(batch))
        self.bulk.wait_for_batch(job,batch)
        self.logger.info('Batch {0} finished'.format(batch))
        self.bulk.close_job(job)
        self.logger.info('Job {0} closed'.format(job))
        with open(self.options['result_file'],"w") as result_file:
            for row in self.bulk.get_batch_result_iter(job,batch):
                result_file.write(row+'\n')
        self.logger.info('Wrote results to: {result_file}'.format(**self.options))
