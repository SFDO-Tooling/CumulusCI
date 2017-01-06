from cumulusci.tasks.salesforce import BaseSalesforceBulkApiTask

import csv
import time
import hiyapyco
import xml.etree.ElementTree as ET

import datetime
import requests
import tempfile

from salesforce_bulk import CsvDictsAdapter

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import text
from sqlalchemy import types
from sqlalchemy import event
from StringIO import StringIO

# Create a custom sqlalchemy field type for sqlite datetime fields which are stored as integer of epoch time
class EpochType(types.TypeDecorator):
    impl = types.Integer

    epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)

    def process_bind_param(self, value, dialect):
        return (value / 1000 - self.epoch).total_seconds()

    def process_result_value(self, value, dialect):
        return self.epoch + datetime.timedelta(seconds=value / 1000)

# Listen for sqlalchemy column_reflect event and map datetime fields to EpochType
@event.listens_for(Table, "column_reflect")
def setup_epoch(inspector, table, column_info):
    if isinstance(column_info['type'], types.DateTime):
        column_info['type'] = EpochType()

class DeleteData(BaseSalesforceBulkApiTask):

    task_options = {
        'objects': {
            'description': 'A list of objects to delete records from in order of deletion.  If passed via command line, use a comma separated string',
            'required': True,
        }
    }

    def _init_options(self, kwargs):
        super(DeleteData, self)._init_options(kwargs)
       
        # Split and trim objects string into a list if not already a list
        if not isinstance(self.options['objects'], list):
            self.options['objects'] = [obj.strip() for obj in self.options['objects'].split(',')]

    def _run_task(self):
        for obj in self.options['objects']:
            self.logger.info('Deleting all {} records'.format(obj))
            # Query for all record ids
            self.logger.info('  Querying for all {} objects'.format(obj))
            query_job = self.bulk.create_query_job(obj, contentType='CSV')
            batch = self.bulk.query(query_job, "select Id from {}".format(obj))
            while not self.bulk.is_batch_done(query_job, batch):
                time.sleep(10)
            self.bulk.close_job(query_job)

            delete_rows = []
            for row in self.bulk.get_batch_result_iter(query_job, batch, parse_csv=True):
                delete_rows.append(row)

            if not delete_rows:
                self.logger.info('  No {} objects found, skipping delete'.format(obj))
                continue

            # Delete the records
            delete_job = self.bulk.create_delete_job(obj, contentType='CSV')
            self.logger.info('  Deleting {} {} records'.format(len(delete_rows), obj))
            batch_num = 1
            for batch in self._upload_batch(delete_job, delete_rows):
                self.logger.info('    Uploaded batch {}'.format(batch))
                while not self.bulk.is_batch_done(delete_job, batch):
                    self.logger.info('      Checking status of batch'.format(batch_num))
                    time.sleep(10)
                self.logger.info('      Batch {} complete'.format(batch))
                batch_num += 1
            self.bulk.close_job(delete_job)

    def _split_batches(self, data, batch_size):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(data), batch_size):
            yield data[i:i + batch_size]

    def _upload_batch(self, job, data):
        # Split into batches
        batches = self._split_batches(data, 2500)

        uri = "{}/job/{}/batch".format(self.bulk.endpoint, job)
        headers = self.bulk.headers({"Content-Type": "text/csv"})
        for batch in batches:
            data = ['"Id"']
            data += ['"{}"'.format(record['Id']) for record in batch]
            data = '\n'.join(data)
            resp = requests.post(uri, data=data, headers=headers)
            content = resp.content

            if resp.status_code >= 400:
                self.bulk.raise_error(content, resp.status_code)

            tree = ET.fromstring(content)
            batch_id = tree.findtext("{%s}id" % self.bulk.jobNS)

            yield batch_id
        
class LoadData(BaseSalesforceBulkApiTask):

    task_options = {
        'database_url': {
            'description': 'The database url to a database containing the test data to load',
            'required': True,
        },
        'mapping': {
            'description': 'The path to a yaml file containing mappings of the database fields to Salesforce object fields',
            'required': True,
        },
    }

    def _run_task(self):
        self._init_mapping()
        self._init_db()

        for name, mapping in self.mapping.items():
            self.logger.info('Running Job: {}'.format(name))
            rows = self._get_batches(mapping)
            res = self._upload_batches(mapping, rows)

    def _create_job(self, mapping):
        action = mapping.get('action', 'insert')
        job_id = None

        if action == 'insert':
            job_id = self.bulk.create_insert_job(mapping['sf_object'], contentType='CSV')

        if not job_id:
            self.logger.error('  No handler for action type {}'.format(action))

        self.logger.info('  Created bulk job {}'.format(job_id))

        return job_id


    def _upload_batches(self, mapping, batches):
      
        job_id = None
        table = self.tables[mapping.get('table')]

        for batch, batch_rows in batches:
            if not job_id:
                # Create a job only once we have the first batch to load into it
                job_id = self._create_job(mapping)

            # Prepare the rows
            rows = CsvDictsAdapter(iter(batch))

            # Create the batch
            batch_id = self.bulk.post_bulk_batch(job_id, rows)
            self.logger.info('    Uploaded batch {}'.format(batch_id))
            while not self.bulk.is_batch_done(job_id, batch_id):
                self.logger.info('      Checking batch status...')
                time.sleep(10)
            
            # Wait for batch to complete
            res = self.bulk.wait_for_batch(job_id, batch_id)
            self.logger.info('      Batch {} complete'.format(batch_id))

            # salesforce_bulk is broken in fetching id results so do it manually
            results_url = '{}/job/{}/batch/{}/result'.format(self.bulk.endpoint, job_id, batch_id)
            headers = self.bulk.headers()
            resp = requests.get(results_url, headers=headers)
            csv_file = tempfile.TemporaryFile()
            csv_file.write(resp.content)
            csv_file.seek(0)
            reader = csv.DictReader(csv_file)

            # Write to the local Id column on the uploaded rows
            i = 0
            for result in reader:
                row = batch_rows[i]
                i += 1
                if result['Id']:
                    setattr(row, mapping['fields']['Id'], result['Id'])

            # Commit to the db
            self.session.commit()
                
        self.bulk.close_job(job_id)
 
        
    def _query_db(self, mapping):
        table = self.tables[mapping.get('table')]

        query = self.session.query(table)
        if 'filters' in mapping:
            filter_args = []
            for f in mapping['filters']:
                filter_args.append(text(f))
            query = query.filter(*filter_args)
        return query


    def _get_batches(self, mapping):
        action = mapping.get('action', 'insert')
        fields = mapping.get('fields', {}).copy()
        static = mapping.get('static', {})
        lookups = mapping.get('lookups', {})
        record_type = mapping.get('record_type')

        # Skip Id field on insert
        if action == 'insert' and 'Id' in fields:
            del fields['Id']

        # Build the list of fields to import
        import_fields = fields.keys() + static.keys() + lookups.keys()
        
        if record_type:
            import_fields.append('RecordTypeId')
            # query for record type by dev name
            record_type_id = None

        query = self._query_db(mapping)

        total_rows = 0
        batch_num = 1
        batch = []
        batch_rows = []
    
        for row in query:
            total_rows += 1

            # Get the row data from the mapping and database values
            csv_row = {}
            for key, value in fields.items():
                csv_row[key] = getattr(row, value)
            for key, value in static.items():
                csv_row[key] = value
            for key, lookup in lookups.items():
                lookup_table = lookup['table']
                kwargs = {lookup['join_field']: getattr(row, lookup['key_field'])}
                try:
                    res = self.session.query(self.tables[lookup['table']]).filter_by(**kwargs).one()
                    csv_row[key] = getattr(res, lookup['value_field'])
                except:
                    csv_row[key] = None
            if record_type:
                csv_row['RecordTypeId'] = record_type_id 

            # utf-8 encode row values
            for key, value in csv_row.items():
                if value:
                    if isinstance(value, datetime.datetime):
                        csv_row[key] = value.isoformat()
                    else:
                        try:
                            csv_row[key] = value.encode('utf8')
                        except AttributeError:
                            continue

            # Write to csv file
            batch.append(csv_row)
        
            batch_rows.append(row)

            # Slice into batches
            if len(batch) == 10000:
                self.logger.info('    Processing batch {}'.format(batch_num))
                yield batch, batch_rows

                # Start the next batch
                batch_num += 1
                batch = []
                batch_rows = []

        self.logger.info('  Prepared {} rows for import to {}'.format(total_rows, mapping['sf_object']))

        if batch:
            yield batch, batch_rows

    def _init_db(self):
        # initialize the DB engine
        self.engine = create_engine(self.options['database_url'])

        # initialize DB metadata
        self.metadata = MetaData()
        self.metadata.bind = self.engine

        # initialize the automap mapping
        self.base = automap_base(bind=self.engine, metadata=self.metadata)
        self.base.prepare(self.engine, reflect=True)

        # Loop through mappings and reflect each referenced table
        self.tables = {}
        for name, mapping in self.mapping.items():
            if 'table' in mapping and mapping['table'] not in self.tables:
                self.tables[mapping['table']] = self.base.classes[mapping['table']]

        # initialize the DB session
        self.session = Session(self.engine)

    def _init_mapping(self):
        self.mapping = hiyapyco.load(self.options['mapping'])
