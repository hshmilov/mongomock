import asyncio
import json
import time

import aiohttp
import pytest

from axonius.async.utils import async_request

SERVER = 'https://127.0.0.1:33443'


def test_https_verify():
    response = list(async_request([{'method': 'get', 'url': f'{SERVER}/echo/something'}]))
    assert isinstance(response[0], aiohttp.ClientConnectionError)


def test_parallel_get():
    # Async get for a couple of requests, each one of them should take 3 seconds, we need to see
    # that we get everything in 3 seconds
    start = time.time()
    response = async_request([
        {'method': 'get', 'url': f'{SERVER}/echo/something1?sleep=3', 'ssl': False},
        {'method': 'get', 'url': f'{SERVER}/echo/something2?sleep=3', 'ssl': False},
        {'method': 'get', 'url': f'{SERVER}/echo/something3?sleep=3', 'ssl': False}
    ])
    end = time.time()
    assert (end - start) < 3.5

    response = list(response)
    for i, r in enumerate(response):
        text, robject = r
        assert text == f'something{i+1}'
        assert robject.status == 200


def test_headers():
    # Test that we indeed send headers
    text, response_object = list(async_request([
        {'method': 'get', 'url': f'{SERVER}/headers', 'ssl': False, 'headers': {'Header1': 'value1'}}
    ]))[0]

    headers = json.loads(text)
    assert headers['Header1'] == 'value1'


def test_url_params():
    text, response_object = list(async_request([{'method': 'get', 'url': f'{SERVER}/url_params',
                                                 'params': {'param1': 'value1'}, 'ssl': False}]))[0]

    response = json.loads(text)
    assert response['param1'] == 'value1'


def test_body_params():
    text, response_object = list(async_request([{'method': 'post', 'url': f'{SERVER}/body_params',
                                                 'json': {'param1': 'value1'}, 'ssl': False}]))[0]

    response = json.loads(text)
    assert response['param1'] == 'value1'


def test_timeout():
    # Send multiple requests, one of them should fail on timeout.
    start = time.time()
    response = async_request([
        {'method': 'get', 'url': f'{SERVER}/echo/something1', 'ssl': False, 'timeout': (1, 1)},
        {'method': 'get', 'url': f'{SERVER}/echo/something2?sleep=10', 'ssl': False, 'timeout': (1, 1)},
        {'method': 'get', 'url': f'{SERVER}/echo/something3', 'ssl': False, 'timeout': (1, 1)}
    ])
    end = time.time()
    assert (end - start) < 3

    response = list(response)
    assert response[0][0] == 'something1'
    assert response[2][0] == 'something3'

    # On different environments (different versions of aiohttp and asyncio), different timeout exceptions are thrown.
    exc_type = type(response[1])
    assert exc_type in (aiohttp.client_exceptions.ServerTimeoutError, asyncio.TimeoutError)


def test_basic_auth():
    # Test that basic auth works. First, without authenticating, then, with authenticating.
    text, response = list(async_request([{'method': 'get',
                                          'url': f'{SERVER}/echo/something',
                                          'params': {'basic_auth_username': 'username',
                                                     'basic_auth_password': 'password'},
                                          'ssl': False}]))[0]
    with pytest.raises(aiohttp.ClientResponseError):
        response.raise_for_status()

    text, response = list(async_request([{'method': 'get',
                                          'url': f'{SERVER}/echo/something',
                                          'params': {'basic_auth_username': 'username',
                                                     'basic_auth_password': 'password'},
                                          'auth': ('username', 'password'),
                                          'ssl': False}]))[0]
    response.raise_for_status()


def test_http_error_in_result():
    # Test some error codes that might happen like 404 file not found.
    text, response = list(async_request([{'method': 'get',
                                          'url': f'{SERVER}/error/205/some_error',
                                          'ssl': False}]))[0]

    assert response.status == 205
    assert text == 'some_error'


@pytest.mark.skip('We don\'t have a proxy, that\'s a TODO')
def test_proxy():
    # Test that we indeed go through proxy.
    pass
