import json
import pytest
import html

from restomatic.wsgi_endpoint_router import EndpointRouter, EndpointRouterBadDefinition, EndpointRouterBadInput

from restomatic.wsgi_debugger import WSGIDebugger


def endpt_index(request):
    return 'Hello World!'


def endpt_catch_all(request):
    return 'Interesting content, for sure'


def endpt_denied(request):
    return "I can't let you do that, Dave.", 401, [('Content-Length', '30')]


def endpt_extra_header(request):
    return 'Totally a normal page', 200, {'X-Secret-Header': 'Super Secret'}


def endpt_override_text(request):
    return 'Actually just plain text', 200, [('Content-Type', 'text/plain; charset=utf-8')]


def endpt_echo(request):
    return {'You sent this uri': request['uri']['path']}


def endpt_echo_body(request):
    return {'You sent this request body': request['body']}


def endpt_echo_body_plain(request):
    return f'You sent this request body: {html.escape(request["body"])}'


def endpt_echo_body_html(request):
    body_data_str = html.escape(f'{request["body"]}')
    return f'<html><head></head><body>You sent this request body: {body_data_str}</body></html>'


def endpt_exception(request):
    x = int('whoops')
    return f'OK! {x}'


def test_endpoint_router_main():
    router = EndpointRouter()

    router.register_endpoint(endpt_index, exact=['/', '/index.html'], method='GET')
    router.register_endpoint(endpt_denied, exact='/denied', method='GET', disallow_other_methods=True)
    router.register_endpoint(endpt_extra_header, exact='/extra_header', method='PUT')
    router.register_endpoint(endpt_echo, prefix='/echo', method='GET', out_format='json')
    router.register_endpoint(endpt_echo_body, exact='/echo_body', method='PATCH', in_format='json', out_format='json')
    router.register_endpoint(endpt_echo_body_plain, exact='/echo_body_plain', method='PATCH', in_format='plain', out_format='plain')
    router.register_endpoint(endpt_echo_body_html, exact='/echo_body_html', method='PATCH', in_format='form', out_format='html')
    router.register_endpoint(endpt_exception, exact='/whoops', method='GET', out_format='html')
    router.register_endpoint(static_data='Hi!', exact='/hi', method='GET', out_format='plain')
    router.register_endpoint(static_file='LICENSE', exact='/license', method='GET', out_format='plain')
    router.register_endpoint(endpt_override_text, prefix='/override', method='GET', out_format='html')

    wsgi = WSGIDebugger(router.application)

    response = wsgi.test_endpoint('GET', '/')
    assert response == 'Hello World!'
    assert wsgi.status == '200 OK'
    assert wsgi.headers == [('Content-Type', 'text/plain; charset=utf-8'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('GET', '/index.html')
    assert response == 'Hello World!'
    assert wsgi.status == '200 OK'
    assert wsgi.headers == [('Content-Type', 'text/plain; charset=utf-8'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('GET', '/not_found')
    assert response == '404 Not Found'
    assert wsgi.status == '404 Not Found'
    assert wsgi.headers == [('Content-Type', 'text/plain; charset=utf-8'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('GET', '/denied')
    assert response == "I can't let you do that, Dave."
    assert wsgi.status == '401 Unauthorized'
    assert wsgi.headers == [('Content-Length', str(len(response))), ('Content-Type', 'text/plain; charset=utf-8')]

    response = wsgi.test_endpoint('POST', '/denied')
    assert response == '405 Method Not Allowed'
    assert wsgi.status == '405 Method Not Allowed'
    assert wsgi.headers == [('Content-Type', 'text/plain; charset=utf-8'), ('Allow', 'GET'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('PUT', '/extra_header')
    assert response == "Totally a normal page"
    assert wsgi.status == '200 OK'
    assert wsgi.headers == [('X-Secret-Header', 'Super Secret'), ('Content-Type', 'text/plain; charset=utf-8'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('GET', '/echo/hi')
    assert json.loads(response) == {'You sent this uri': '/echo/hi'}
    assert wsgi.status == '200 OK'
    assert wsgi.headers == [('Content-Type', 'application/json; charset=utf-8'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('GET', '/whoops')
    assert response == """<!DOCTYPE html>
<html>
<head>
<title>500 Internal Server Error</title>
</head>
<body>
ValueError: invalid literal for int() with base 10: &#x27;whoops&#x27;
</body>
</html>
"""
    assert wsgi.status == '500 Internal Server Error'
    assert wsgi.headers == [('Content-Type', 'text/html; charset=utf-8'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('PATCH', '/echo_body', json.dumps({'testing': 'yep'}))
    assert json.loads(response) == {'You sent this request body': {'testing': 'yep'}}
    assert wsgi.status == '200 OK'
    assert wsgi.headers == [('Content-Type', 'application/json; charset=utf-8'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('PATCH', '/echo_body', '{"Probably not valid JSON": ')
    assert json.loads(response) == {'message': 'Failed to parse JSON input: Expecting value: line 1 column 29 (char 28)'}
    assert wsgi.status == '400 Bad Request'
    assert wsgi.headers == [('Content-Type', 'application/json; charset=utf-8'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('PATCH', '/echo_body_plain', 'Additional & Information')
    assert response == 'You sent this request body: Additional &amp; Information'
    assert wsgi.status == '200 OK'
    assert wsgi.headers == [('Content-Type', 'text/plain; charset=utf-8'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('PATCH', '/echo_body_html', 'source=Neither+Here+Nor+There&data=100%25%21')
    assert response == ('<html><head></head><body>'
                        'You sent this request body: '
                        '{&#x27;source&#x27;: [&#x27;Neither Here Nor There&#x27;], &#x27;data&#x27;: [&#x27;100%!&#x27;]}'
                        '</body></html>')
    assert wsgi.status == '200 OK'
    assert wsgi.headers == [('Content-Type', 'text/html; charset=utf-8'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('GET', '/hi')
    assert response == 'Hi!'
    assert wsgi.status == '200 OK'
    assert wsgi.headers == [('Content-Type', 'text/plain; charset=utf-8'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('GET', '/license')
    with open('LICENSE') as f:
        assert response == f.read()
    assert wsgi.status == '200 OK'
    assert wsgi.headers == [('Content-Type', 'text/plain; charset=utf-8'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('GET', '/override')
    assert response == 'Actually just plain text'
    assert wsgi.status == '200 OK'
    assert wsgi.headers == [('Content-Type', 'text/plain; charset=utf-8'), ('Content-Length', str(len(response)))]

    response = wsgi.test_endpoint('PATCH', '/override')
    assert response == """<!DOCTYPE html>
<html>
<head>
<title>405 Method Not Allowed</title>
</head>
<body>
405 Method Not Allowed
</body>
</html>
"""
    assert wsgi.status == '405 Method Not Allowed'
    assert wsgi.headers == [('Content-Type', 'text/html; charset=utf-8'), ('Allow', 'GET'), ('Content-Length', str(len(response)))]


def test_bad_definitions():
    router = EndpointRouter()

    with pytest.raises(EndpointRouterBadDefinition):
        router.register_endpoint(None, exact='/', method='GET')

    with pytest.raises(EndpointRouterBadDefinition):
        router.register_endpoint(endpt_catch_all, prefix='/', method='GET', disallow_other_methods=True)


def test_exceptions():
    bad_definition = EndpointRouterBadDefinition('message', 401, {'found exception': 'here'})

    assert bad_definition.status_code == 401
    assert bad_definition.to_dict() == {'found exception': 'here', 'message': 'message'}

    bad_input = EndpointRouterBadInput('message', 401, {'found exception': 'here'})

    assert bad_input.status_code == 401
    assert bad_input.to_dict() == {'found exception': 'here', 'message': 'message'}
