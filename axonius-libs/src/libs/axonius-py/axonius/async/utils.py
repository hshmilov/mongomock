"""
Async io utilities.
"""
import asyncio
import ssl
import typing
import logging
from inspect import isawaitable
from aiohttp import ClientSession, ClientTimeout, ClientResponse, BasicAuth, TCPConnector
logger = logging.getLogger(f'axonius.{__name__}')


async def async_http_request(session: ClientSession, callback=None, **kwargs):
    """
    Makes an async request
    :param session: the session object
    :param callback: callback function to be called after the http request.
                     callback function should be:
                     callback(response_text: str, response: aiohttp.ClientResponse, session: Clientsession)
                     callback may be an async function (good practice) or a sync function.
    :param kwargs: all parameters to session.request, e.g. {method: "get", "url": "..",
                                                            params={'q1': 'a1'}, headers={}}
                   more: https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request
    :return:
    """
    # Fix some values
    if kwargs.get('timeout') is not None:
        timeout_connect, timeout_read = kwargs['timeout']
        kwargs['timeout'] = ClientTimeout(connect=timeout_connect, sock_read=timeout_read)
    if kwargs.get('auth') is not None:
        kwargs['auth'] = BasicAuth(*kwargs['auth'])

    # This is a setting for us, and not for session.request
    get_binary = bool(kwargs.get('get_binary'))
    kwargs.pop('get_binary', None)

    # Send the request
    async with session.request(**kwargs) as response:
        if get_binary is True:
            binary_response = await response.read()
            return binary_response, response

        text = await response.text()
        if callback:
            # call callback function and handle async callback functions
            callback_function = callback(text, response, session)
            if isawaitable(callback_function):
                await callback(text, response, session)
        return text, response


async def run(reqs, **kwargs):
    tasks = []
    # Fetch all responses within one Client session,
    # keep connection alive for all requests.A
    ssl_ctx = None
    if kwargs.get('cert') is not None:
        cert = kwargs.get('cert')
        ssl_ctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(*cert)
    connector = TCPConnector(limit=None, ssl_context=ssl_ctx)
    responses = None
    async with ClientSession(connector=connector) as session:
        for req in reqs:
            task = asyncio.ensure_future(async_http_request(session, **req))
            tasks.append(task)

        # return_exceptions=True means that we don't propogate exceptions up, we just return all exceptions as
        # the result of the requests.
        # so the result can be ["first_result", "second_result", Exception(...), "fourth_result"]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
    connector.close()
    return responses


def async_request(req_list: list, **kwargs) -> typing.List[ClientResponse]:
    """
    Makes requests
    :param req_list: a list of dict for making a request.
    :return: a list of aio.ClientResponse. If an exception occurs, the output of it will be an Exception object.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    future = asyncio.ensure_future(run(req_list, **kwargs))
    result = loop.run_until_complete(future)
    # Wait 250 ms for the underlying SSL connections to close
    # https://aiohttp.readthedocs.io/en/stable/client_advanced.html
    loop.run_until_complete(asyncio.sleep(0.250))
    return result
