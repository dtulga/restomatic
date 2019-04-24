# Rest-o-matic
Automatic JSON-based API generator, including a SQL Query Compositor and WSGI Endpoint Router

## Warning: This software is in alpha, and API or function signatures may change before full release.

## Usage
This package includes three primary components:

### Rest-o-matic Endpoints / API Description
This system generates JSON endpoints automatically for tables utilizing the included
SQL Query Compositor and WSGI Endpoint router

Create a new set of endpoints with the command:
```
from restomatic.json_sql_compositor import SQLiteDB
from restomatic.wsgi_endpoint_router import EndpointRouter
from restomatic.endpoint import register_restomatic_endpoint

table_mappers = {
    'table_name': ['column1', 'column2', ...],
    ...
}

db = SQLiteDB(database_filename, table_mappers)

router = EndpointRouter()

register_restomatic_endpoint(router, db, 'table_name', ['GET', 'PUT', 'POST', 'PATCH', 'DELETE'])
...
```
Any set of methods is valid to allow. Methods not provided will return 405 Method Not Allowed errors
if disallow_other_methods is set to True.

### GET (returns 200 if found, 404 if no match)
```
GET one: /table/1
```
Returns: The requested row as a JSON object (dictionary)

### POST (returns 201 for create, 200 for search, on success)
This endpoint creates a new row (or multiple new rows) 
Also supports a get-like search (but without the limits on uri size/format)
```
POST one: /table
    body: {...}
or POST many: /table
    body: [{...}, {...}]
or POST-based search: /table/search (returns 200 if found, 404 if no matches)
    body: {'where': [...search criteria...]}
    Optionally, can also include in addition to the where clause:
    'limit': 1, 'offset': 2, 'order_by': ['column_1', {'column': 'column_2', 'direction': 'ASC'}]
```
The IDs of the created instances are returned as well.

### PUT (returns 200 on success)
This endpoint can create or update the given rows
```
PUT one: /table
    body: {...} (if ID specified, update, otherwise create)
or PUT many: /table
    body: [{...}, {...}] (if ID specified, update, otherwise create)
```

### PATCH (returns 200 on success)
This endpoint updates the given row or based on the given where condition
```
PATCH one: /table/1
    body: {...}
or PATCH many: /table/where
    body: {'where': [...search criteria...], 'set': {...}}
```

### DELETE (returns 200 on success)
This endpoint deletes the given row or based on the given where condition 
```
DELETE one: /table/1
or DELETE many: /table/where
    body: {'where': [...search criteria...]}
```

### Search Criteria Format
The search criteria is a list which contains two or three elements,
the column, an operator to compare, and a value (unless the operator does not need a value.)
In addition, search criteria can be combined with 'and' or 'or' by adding all
desired comparison statements (two or three element lists) into a list with a dictionary with
either 'and' or 'or' as the key. (See example below)

Search Criteria Examples:
```
['id', 'isnotnull']
['id', 'eq', 1]
['value', 'lt', 1.3]
['id', 'gte', 2]
['description', 'like', '%ABC%']
['value', 'isnull']
['description', 'in', ['test 1', 'test 5']]
['description', 'not_in', ['test 1', 'test 2', 'test 3']]
```

Operators should be one of:
```
'eq', '=', '=='
'lt', '<'
'gt', '>'
'lte', '<='
'gte', '>='
'in'
'notin', 'not_in'
'like'
'isnull', 'is_null'
'isnotnull', 'is_not_null'
```
(Operators in each row are equivalent)

Example Search:
```
POST /test/search
{'where': ['id', 'lte', 3]}
```

With an AND statement:
```
POST /test/search
{
    'where': {
        'and': [
            ['id', 'lte', 3],
            ['id', '>', 1]
        ]
    }
}
```

### SQL Query Compositor / SQLite DB Interface
This provides a convenient and secure way of interacting with a local SQLite DB,
allowing one to construct SQL queries through python functions, rather than by
string manipulation. It also supports parameter binding, to prevent the most common
kind of SQL injection attacks.

To utilize the query compositor, first create a database reference:

```
db = SQLiteDB('test.db', table_mappers)
```

This will create the database file (but not the tables) if it does not exist.
You can also provide ':memory:' for an in-memory-only sqlite database.

Then one can perform select, update, insert, and delete statements as such:

```
db.select_all('test').where({'and': [['id', 'gte', 2], ['id', 'lt', 3]]}).one() == (2, 'test 2', 1.5)
db.select_all('test').where(['id', 'isnotnull']).all_mapped() == [{'id': 1, 'description': 'test 1', 'value': 0.5}]
db.select_all('test').count().scalar() == 2
db.select_all('test').where(['id', 'gte', 3]).one_or_none_mapped() is None
db.insert('test', ('description', 'value')).values(('test 2', 1.5))
db.insert_mapped('test', ({'description': 'test 3', 'value': 3.0}, {'description': 'test 4', 'value': 4.4}))
db.delete('test').where(('id', 'eq', 4)).run()
db.update_mapped('test', {'value': 2.0}).where(('id', 'eq', 1)).run()
db.commit() # Required for persisting any transactional changes.
```

Note that generally the _mapped() forms will return a JSON-like dict, the plain forms will return tuples in
either the table order (for select_all) or the columns provided order (if columns are specified). In addition,
scalar() will return a the first value only, such as for count queries. In addition, all() functions return
lists of results, while one() returns only one (and will raise an error if not found), and one_or_none()
returns either one result or None if not found.

Also note that the format used by the filter functions (such as where and order_by) is the same as the API
format described above and utilized by the restomatic endpoints.

See the test file for a full treatment on all possible usages and return values/formats.

### WSGI Endpoint Router

This provides a lightweight and convenient way of routing multiple endpoints based on request method
(GET, PUT, POST, PATCH, DELETE) and the requested uri (such as /index or /table). It also supports
both exact-match and prefix-match for uris, and auto-parses/returns formats of plain text, JSON, and
form-input, html-output.

It can be instantiated with:
```
from restomatic.wsgi_endpoint_router import EndpointRouter

router = EndpointRouter(default_in_format='plain', default_out_format='plain')
```
Optionally specifying the server default formats.

Endpoints are then registered as:
```
router.register_endpoint(endpt_index, exact='/', method='GET')
router.register_endpoint(endpt_get_json, prefix='/get_json', method='GET', out_format='json')
router.register_endpoint(endpt_patch_json, exact='/patch_json', method='PATCH', in_format='json', out_format='json')
```
With each endpoint definition specifying first the function to handle the endpoint call, and
allowed to specify either an exact or prefix match, an HTTP method to handle,
and in and out format to automatically handle.

Endpoint functions have this signature:
```
def endpoint_index(request):
    ...create data...
    return data
```
The return value can be either of:
```
response_data
response_data, status_code
response_data, status_code, additional_headers
```
Where additional headers can either be in the format:
```
{'X-Example': 'Header-Value'}
```
or
```
[('Content-Type', 'text/plain')]
```
If the content-type header is provided, it can be used to override the default based on the endpoint definition.

See the test file for a full treatment on all possible usages and return values/formats.

## Install

Requires Python 3.6+ with no other external dependencies.
However, a WSGI server will be required, such as uWSGI.

To use uWSGI, you can install it as such:

```
pip3 install uwsgi
```

You may need dependent packages (depending upon the system) such as python3-dev and build-essential
to install uWSGI, for full instructions see: https://uwsgi-docs.readthedocs.io/en/latest/WSGIquickstart.html

In addition, to run the unit tests, pytest is required, and pytest-cov recommended.

## Planned Features

* Greater database support, including PostgreSQL / MySQL
* Support for more types, such as enums and booleans
* Automatic table creation, plus check constraints (for ranges/positive/etc.)
* Support for pre- and post- processing data for better validation and structure
* Ability to use decorators, authorization, and logging for better security and customization
* Support for JOINs and possibly foreign key relationship loading
* Support for Flask (option to be used instead of the provided WSGI router)
