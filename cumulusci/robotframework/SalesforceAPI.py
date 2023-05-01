from simple_salesforce.exceptions import SalesforceResourceNotFound

from cumulusci.core.template_utils import format_str
from cumulusci.robotframework.base_library import BaseLibrary

# https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_composite_sobjects_collections_create.htm
SF_COLLECTION_INSERTION_LIMIT = 200
STATUS_KEY = ("status",)


class SalesforceAPI(BaseLibrary):
    """Keywords for interacting with Salesforce API"""

    def __init__(self):
        super().__init__()
        self._session_records = []

    def delete_session_records(self):
        """Deletes records that were created while running this test case.

        (Only records specifically recorded using the Store Session Record
        keyword are deleted.)
        """
        self._session_records.reverse()
        self.builtin.log("Deleting {} records".format(len(self._session_records)))
        for record in self._session_records[:]:
            self.builtin.log("  Deleting {type} {id}".format(**record))
            try:
                self.salesforce_delete(record["type"], record["id"])
            except SalesforceResourceNotFound:
                self.builtin.log("    {type} {id} is already deleted".format(**record))
            except Exception as e:
                self.builtin.log(
                    "    {type} {id} could not be deleted:".format(**record),
                    level="WARN",
                )
                self.builtin.log("      {}".format(e), level="WARN")

    def get_latest_api_version(self):
        """Return the API version used by the current org"""
        return self.cumulusci.org.latest_api_version

    def get_record_type_id(self, obj_type, developer_name):
        """Returns the Record Type Id for a record type name"""
        soql = "SELECT Id FROM RecordType WHERE SObjectType='{}' and DeveloperName='{}'".format(
            obj_type, developer_name
        )
        res = self.cumulusci.sf.query_all(soql)
        return res["records"][0]["Id"]

    def salesforce_delete(self, obj_name, obj_id):
        """Deletes a Salesforce object by object name and Id.

        Example:

        The following example assumes that ``${contact id}`` has been
        previously set. The example deletes the Contact with that Id.

        | Salesforce Delete  Contact  ${contact id}
        """
        self.builtin.log("Deleting {} with Id {}".format(obj_name, obj_id))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        obj_class.delete(obj_id)
        self.remove_session_record(obj_name, obj_id)

    def salesforce_get(self, obj_name, obj_id):
        """Gets a Salesforce object by Id and returns the result as a dict.

        Example:

        The following example assumes that ``${contact id}`` has been
        previously set. The example retrieves the Contact object with
        that Id and then logs the Name field.

        | &{contact}=  Salesforce Get  Contact  ${contact id}
        | log  Contact name:  ${contact['Name']}

        """
        self.builtin.log(f"Getting {obj_name} with Id {obj_id}")
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.get(obj_id)

    def salesforce_insert(self, obj_name, **kwargs):
        """Creates a new Salesforce object and returns the Id.

        The fields of the object may be defined with keyword arguments
        where the keyword name is the same as the field name.

        The object name and Id is passed to the *Store Session
        Record* keyword, and will be deleted when the keyword
        *Delete Session Records* is called.

        As a best practice, either *Delete Session Records* or
        *Delete Records and Close Browser* from Salesforce.robot
        should be called as a suite teardown.

        Example:

        The following example creates a new Contact with the
        first name of "Eleanor" and the last name of "Rigby".

        | ${contact id}=  Salesforce Insert  Contact
        | ...  FirstName=Eleanor
        | ...  LastName=Rigby

        """
        self.builtin.log("Inserting {} with values {}".format(obj_name, kwargs))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        res = obj_class.create(kwargs)
        self.store_session_record(obj_name, res["id"])
        return res["id"]

    def _salesforce_generate_object(self, obj_name, **fields):
        obj = {"attributes": {"type": obj_name}}  # Object type to create
        obj.update(fields)
        return obj

    def generate_test_data(self, obj_name, number_to_create, **fields):
        """Generate bulk test data

        This returns an array of dictionaries with template-formatted
        arguments which can be passed to the *Salesforce Collection Insert*
        keyword.

        You can use ``{{number}}`` to represent the unique index of
        the row in the list of rows.  If the entire string consists of
        a number, Salesforce API will treat the value as a number.

        Example:

        The following example creates three new Contacts:

            | @{objects} =  Generate Test Data  Contact  3
            | ...  Name=User {{number}}
            | ...  Age={{number}}

        The example code will generate Contact objects with these fields:

            | [{'Name': 'User 0', 'Age': '0'},
            |  {'Name': 'User 1', 'Age': '1'},
            |  {'Name': 'User 2', 'Age': '2'}]

        Python Expression Syntax is allowed so computed templates like this are also allowed: ``{{1000 + number}}``

        Python operators can be used, but no functions or variables are provided, so mostly you just
        have access to mathematical and logical operators. The Python operators are described here:

        https://www.digitalocean.com/community/tutorials/how-to-do-math-in-python-3-with-operators

        Contact the CCI team if you have a use-case that
        could benefit from more expression language power.

        Templates can also be based on faker patterns like those described here:

        https://faker.readthedocs.io/en/master/providers.html

        Most examples can be pasted into templates verbatim:

            | @{objects}=  Generate Test Data  Contact  200
            | ...  Name={{fake.first_name}} {{fake.last_name}}
            | ...  MailingStreet={{fake.street_address}}
            | ...  MailingCity=New York
            | ...  MailingState=NY
            | ...  MailingPostalCode=12345
            | ...  Email={{fake.email(domain="salesforce.com")}}

        """
        objs = []

        for i in range(int(number_to_create)):
            formatted_fields = {
                name: format_str(value, {"number": i}) for name, value in fields.items()
            }
            newobj = self._salesforce_generate_object(obj_name, **formatted_fields)
            objs.append(newobj)

        return objs

    def remove_session_record(self, obj_type, obj_id):
        """Remove a record from the list of records that should be automatically removed."""
        try:
            self._session_records.remove({"type": obj_type, "id": obj_id})
        except ValueError:
            self.builtin.log(
                "Did not find record {} {} in the session records list".format(
                    obj_type, obj_id
                )
            )

    def salesforce_collection_insert(self, objects):
        """Inserts records that were created with *Generate Test Data*.

        _objects_ is a list of data, typically generated by the
        *Generate Test Data* keyword.

        A 200 record limit is enforced by the Salesforce APIs.

        The object name and Id is passed to the *Store Session
        Record* keyword, and will be deleted when the keyword *Delete
        Session Records* is called.

        As a best practice, either *Delete Session Records* or
        **Delete Records and Close Browser* from Salesforce.robot
        should be called as a suite teardown.

        Example:

        | @{objects}=  Generate Test Data  Contact  200
        | ...  FirstName=User {{number}}
        | ...  LastName={{fake.last_name}}
        | Salesforce Collection Insert  ${objects}

        """
        assert (
            not obj.get("id", None) for obj in objects
        ), "Insertable objects should not have IDs"
        assert len(objects) <= SF_COLLECTION_INSERTION_LIMIT, (
            "Cannot insert more than %s objects with this keyword"
            % SF_COLLECTION_INSERTION_LIMIT
        )

        records = self.cumulusci.sf.restful(
            "composite/sobjects",
            method="POST",
            json={"allOrNone": True, "records": objects},
        )

        for idx, (record, obj) in enumerate(zip(records, objects)):
            if record["errors"]:
                raise AssertionError(
                    "Error on Object {idx}: {record} : {obj}".format(**vars())
                )
            self.store_session_record(obj["attributes"]["type"], record["id"])
            obj["id"] = record["id"]
            obj[STATUS_KEY] = record

        return objects

    def salesforce_collection_update(self, objects):
        """Updates records described as Robot/Python dictionaries.

        _objects_ is a dictionary of data in the format returned
        by the *Salesforce Collection Insert* keyword.

        A 200 record limit is enforced by the Salesforce APIs.

        Example:

        The following example creates ten accounts and then updates
        the Rating from "Cold" to "Hot"

        | ${data}=  Generate Test Data  Account  10
        | ...  Name=Account #{{number}}
        | ...  Rating=Cold
        | ${accounts}=  Salesforce Collection Insert  ${data}
        |
        | FOR  ${account}  IN  @{accounts}
        |     Set to dictionary  ${account}  Rating  Hot
        | END
        | Salesforce Collection Update  ${accounts}

        """
        for obj in objects:
            assert obj[
                "id"
            ], "Should be a list of objects with Ids returned by Salesforce Collection Insert"
            if STATUS_KEY in obj:
                del obj[STATUS_KEY]

        assert len(objects) <= SF_COLLECTION_INSERTION_LIMIT, (
            "Cannot update more than %s objects with this keyword"
            % SF_COLLECTION_INSERTION_LIMIT
        )

        records = self.cumulusci.sf.restful(
            "composite/sobjects",
            method="PATCH",
            json={"allOrNone": True, "records": objects},
        )

        for record, obj in zip(records, objects):
            obj[STATUS_KEY] = record

        for idx, (record, obj) in enumerate(zip(records, objects)):
            if record["errors"]:
                raise AssertionError(
                    "Error on Object {idx}: {record} : {obj}".format(**vars())
                )

    def salesforce_query(self, obj_name, **kwargs):
        """Constructs and runs a simple SOQL query and returns a list of dictionaries.

        By default the results will only contain object Ids. You can
        specify a SOQL SELECT clause via keyword arguments by passing
        a comma-separated list of fields with the ``select`` keyword
        argument.

        You can supply keys and values to match against
        in keyword arguments, or a full SOQL where-clause
        in a keyword argument named ``where``. If you supply
        both, they will be combined with a SOQL "AND".

        ``order_by`` and ``limit`` keyword arguments are also
        supported as shown below.

        Examples:

        The following example searches for all Contacts where the
        first name is "Eleanor". It returns the "Name" and "Id"
        fields and logs them to the robot report:

        | @{records}=  Salesforce Query  Contact  select=Id,Name
        | ...          FirstName=Eleanor
        | FOR  ${record}  IN  @{records}
        |     log  Name: ${record['Name']} Id: ${record['Id']}
        | END

        Or with a WHERE-clause, we can look for the last contact where
        the first name is NOT Eleanor.

        | @{records}=  Salesforce Query  Contact  select=Id,Name
        | ...          where=FirstName!='Eleanor'
        | ...              order_by=LastName desc
        | ...              limit=1
        """
        query = self._soql_query_builder(obj_name, **kwargs)
        self.builtin.log("Running SOQL Query: {}".format(query))
        return self.cumulusci.sf.query_all(query).get("records", [])

    def _soql_query_builder(
        self, obj_name, select=None, order_by=None, limit=None, where=None, **kwargs
    ):
        query = "SELECT "
        if select:
            query += select
        else:
            query += "Id"
        query += " FROM {}".format(obj_name)
        where_clauses = []
        if where:
            where_clauses = [where]
        for key, value in kwargs.items():
            where_clauses.append("{} = '{}'".format(key, value))
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        if order_by:
            query += " ORDER BY " + order_by
        if limit:
            assert int(limit), "Limit should be an integer"
            query += f" LIMIT {limit}"

        return query

    def salesforce_update(self, obj_name, obj_id, **kwargs):
        """Updates a Salesforce object by Id.

        The keyword returns the result from the underlying
        simple_salesforce ``insert`` method, which is an HTTP
        status code. As with `Salesforce Insert`, field values
        are specified as keyword arguments.

        The following example assumes that ${contact id} has been
        previously set, and adds a Description to the given
        contact.

        | &{contact}=  Salesforce Update  Contact  ${contact id}
        | ...  Description=This Contact created during a test
        | Should be equal as numbers ${result}  204

        """
        self.builtin.log(
            "Updating {} {} with values {}".format(obj_name, obj_id, kwargs)
        )
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.update(obj_id, kwargs)

    def soql_query(self, query, *args):
        """Runs a SOQL query and returns the result as a dictionary.

        The _query_ parameter must be a properly quoted SOQL query
        statement or statement fragment. Additional arguments will be
        joined to the query with spaces, allowing for a query to span
        multiple lines.

        This keyword will return a dictionary. The dictionary contains
        the keys as documented for the raw API call. The most useful
        keys are ``records`` and ``totalSize``, which contains a list
        of records that were matched by the query and the number of
        records that were returned.

        Example:

        The following example searches for all Contacts with a first
        name of "Eleanor" and a last name of "Rigby", and then logs
        the Id of the first record found.

        | ${result}=  SOQL Query
        | ...  SELECT Name, Id
        | ...  FROM   Contact
        | ...  WHERE  FirstName='Eleanor' AND LastName='Rigby'
        |
        | ${contact}=  Get from list  ${result['records']}  0
        | log  Contact Id: ${contact['Id']}

        """
        query = " ".join((query,) + args)
        self.builtin.log("Running SOQL Query: {}".format(query))
        return self.cumulusci.sf.query_all(query)

    def store_session_record(self, obj_type, obj_id):
        """Stores a Salesforce record's Id for use in the *Delete Session Records* keyword.

        This keyword is automatically called by *Salesforce Insert*.
        """
        self.builtin.log("Storing {} {} to session records".format(obj_type, obj_id))
        self._session_records.append({"type": obj_type, "id": obj_id})
