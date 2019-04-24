import json
import pytest

from restomatic.endpoint import register_restomatic_endpoint, RestOMaticBadRequest
from restomatic.wsgi_endpoint_router import EndpointRouter
from restomatic.json_sql_compositor import SQLiteDB

from restomatic.wsgi_debugger import WSGIDebugger

table_mappers = {
    'test': ['id', 'description', 'value']
}


def assert_json_response(wsgi, response, status, expected_json):
    assert json.loads(response) == expected_json
    assert wsgi.status == status
    assert wsgi.headers == [('Content-Type', 'application/json')]


def test_restomatic_endpoint_operations():
    db = SQLiteDB(':memory:', table_mappers)

    db.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, description TEXT, value REAL)')

    db.insert_mapped('test', {'description': 'test 1', 'value': 0.5})

    db.commit()

    router = EndpointRouter()

    register_restomatic_endpoint(router, db, 'test', ['GET', 'PUT', 'POST', 'PATCH', 'DELETE'])

    with pytest.raises(RuntimeError):
        register_restomatic_endpoint(router, db, 'test', ['BOGUS'])

    with pytest.raises(RuntimeError):
        register_restomatic_endpoint(router, db, 'bogus', ['GET'])

    wsgi = WSGIDebugger(router.application)

    response = wsgi.test_endpoint('GET', '/test/1')
    assert_json_response(wsgi, response, '200 OK', {'id': 1, 'description': 'test 1', 'value': 0.5})

    response = wsgi.test_endpoint('GET', '/test/a')
    assert_json_response(wsgi, response, '400 Bad Request', {'message': 'Invalid ID, must be a positive integer, 1 or greater'})

    response = wsgi.test_endpoint('GET', '/test')
    assert_json_response(wsgi, response, '400 Bad Request', {'message': 'Must specify an ID for this GET request'})

    response = wsgi.test_endpoint('GET', '/test/42')
    assert_json_response(wsgi, response, '404 Not Found', {'message': 'Requested ID not found'})

    response = wsgi.test_endpoint('PATCH', '/test/1', json.dumps({'value': 1.5}))
    assert_json_response(wsgi, response, '200 OK', {'success': True})

    response = wsgi.test_endpoint('GET', '/test/1')
    assert_json_response(wsgi, response, '200 OK', {'id': 1, 'description': 'test 1', 'value': 1.5})

    response = wsgi.test_endpoint('PATCH', '/test')
    assert_json_response(wsgi, response, '400 Bad Request', {'message': 'Must specify an ID for a PATCH request'})

    response = wsgi.test_endpoint('PATCH', '/test/1')
    assert_json_response(wsgi, response, '400 Bad Request', {'message': 'Must specify a valid JSON object (dictionary) of columns to set for this ID'})

    response = wsgi.test_endpoint('POST', '/test', json.dumps({'description': 'test 2', 'value': 2.5}))
    assert_json_response(wsgi, response, '201 Created', {'success': True, 'id': 2})

    response = wsgi.test_endpoint('GET', '/test/2')
    assert_json_response(wsgi, response, '200 OK', {'id': 2, 'description': 'test 2', 'value': 2.5})

    response = wsgi.test_endpoint('POST', '/test/2')
    assert_json_response(wsgi, response, '400 Bad Request', {'message': 'Cannot specify an ID for a POST request'})

    response = wsgi.test_endpoint('POST', '/test')
    assert_json_response(wsgi, response, '400 Bad Request', {'message': 'Must specify a valid JSON object (dictionary) of columns to set for the new row'})

    response = wsgi.test_endpoint('POST', '/test', json.dumps(['a']))
    assert_json_response(wsgi, response, '400 Bad Request', {'message': 'Must specify a valid JSON object (dictionary) of columns to set for the new row'})

    response = wsgi.test_endpoint('POST', '/test', json.dumps([{'description': 'test 3', 'value': 3.0}, {'description': 'test 4', 'value': 4.4}]))
    assert_json_response(wsgi, response, '201 Created', {'success': True, 'ids': [3, 4]})

    response = wsgi.test_endpoint('POST', '/test/search', json.dumps({'where': ['id', 'lte', 3]}))
    assert_json_response(wsgi, response, '200 OK', {
        'results': [
            {'id': 1, 'description': 'test 1', 'value': 1.5},
            {'id': 2, 'description': 'test 2', 'value': 2.5},
            {'id': 3, 'description': 'test 3', 'value': 3.0}
        ]
    })

    response = wsgi.test_endpoint('POST', '/test/search', json.dumps({
        'where': {
            'and': [
                ['id', 'lte', 3],
                ['id', '>', 1]
            ]
        }
    }))
    assert_json_response(wsgi, response, '200 OK', {
        'results': [
            {'id': 2, 'description': 'test 2', 'value': 2.5},
            {'id': 3, 'description': 'test 3', 'value': 3.0}
        ]
    })

    response = wsgi.test_endpoint('POST', '/test/search', json.dumps({
        'where': ['id', 'lte', 3],
        'limit': 1,
        'offset': 1
    }))
    assert_json_response(wsgi, response, '200 OK', {
        'results': [
            {'id': 2, 'description': 'test 2', 'value': 2.5}
        ]
    })

    response = wsgi.test_endpoint('POST', '/test/search', json.dumps({
        'where': ['id', 'lte', 3],
        'limit': 2,
        'order_by': {
            'column': 'id',
            'direction': 'desc'
        }
    }))
    assert_json_response(wsgi, response, '200 OK', {
        'results': [
            {'id': 3, 'description': 'test 3', 'value': 3.0},
            {'id': 2, 'description': 'test 2', 'value': 2.5}
        ]
    })

    response = wsgi.test_endpoint('POST', '/test/search', json.dumps({
        'where': ['id', 'lte', 3],
        'limit': 2,
        'order_by': {
            'direction': 'desc'
        }
    }))
    assert_json_response(wsgi, response, '400 Bad Request', {
        'message': 'Complex order_by request must contain a column key '
                   'and an optional direction key in the input dictionary'
    })

    response = wsgi.test_endpoint('POST', '/test/search', json.dumps({'where': ['id', 'gte', 10]}))
    assert_json_response(wsgi, response, '200 OK', {'results': None})

    response = wsgi.test_endpoint('POST', '/test/search', json.dumps({
        'where': ['id', 'gte', 10],
        'set': {'value': 11}
    }))
    assert_json_response(wsgi, response, '400 Bad Request', {'message': 'The set JSON object is not valid for this request (did you mean PATCH?)'})

    response = wsgi.test_endpoint('POST', '/test/search')
    assert_json_response(wsgi, response, '400 Bad Request', {'message': 'Must specify a valid JSON object (dictionary) with a valid where parameter list'})

    response = wsgi.test_endpoint('PUT', '/test', json.dumps({'id': 3, 'description': 'test 3', 'value': -3.3}))
    assert_json_response(wsgi, response, '200 OK', {'success': True})

    response = wsgi.test_endpoint('PUT', '/test/1')
    assert_json_response(wsgi, response, '400 Bad Request', {
        'message': 'Cannot specify an ID for a PUT request - all IDs must be specified in the provided JSON objects, '
                   'or use PATCH to update one object by ID'
    })

    response = wsgi.test_endpoint('PUT', '/test', json.dumps([]))
    assert_json_response(wsgi, response, '400 Bad Request', {'message': 'Must specify a valid JSON object (dictionary) of columns to set or update'})

    response = wsgi.test_endpoint('PUT', '/test', json.dumps(['a']))
    assert_json_response(wsgi, response, '400 Bad Request', {'message': 'Must specify a valid JSON object (dictionary) of columns to set or update'})

    response = wsgi.test_endpoint('PUT', '/test', json.dumps([
        {'id': 3, 'description': 'test 3', 'value': -3.0},
        {'description': 'test 5', 'value': 55}
    ]))
    assert_json_response(wsgi, response, '200 OK', {'success': True})

    response = wsgi.test_endpoint('GET', '/test/3')
    assert_json_response(wsgi, response, '200 OK', {'id': 3, 'description': 'test 3', 'value': -3.0})

    response = wsgi.test_endpoint('DELETE', '/test/2')
    assert_json_response(wsgi, response, '200 OK', {'success': True})

    response = wsgi.test_endpoint('GET', '/test/2')
    assert_json_response(wsgi, response, '404 Not Found', {'message': 'Requested ID not found'})

    response = wsgi.test_endpoint('PATCH', '/test/where', json.dumps({
        'where': ['id', 'eq', 5],
        'set': {'value': 55.5}
    }))
    assert_json_response(wsgi, response, '200 OK', {'success': True})

    response = wsgi.test_endpoint('PATCH', '/test/where', json.dumps({'where': ['id', 'eq', 5]}))
    assert_json_response(wsgi, response, '400 Bad Request', {'message': 'Must specify a set JSON object (dictionary) with the columns to be set'})

    response = wsgi.test_endpoint('GET', '/test/5')
    assert_json_response(wsgi, response, '200 OK', {'id': 5, 'description': 'test 5', 'value': 55.5})


def test_exceptions():
    bad_request = RestOMaticBadRequest('message', 401, {'found exception': 'here'})

    assert bad_request.status_code == 401
    assert bad_request.to_dict() == {'found exception': 'here', 'message': 'message'}
