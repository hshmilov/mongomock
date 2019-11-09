"""
Async io utilities.
"""
import asyncio
import ssl
import typing
import logging
from inspect import isawaitable
from aiohttp import ClientSession, ClientTimeout, ClientResponse, BasicAuth, TCPConnector, ClientConnectorError

logger = logging.getLogger(f'axonius.{__name__}')

MAX_RETRIES = 3
DEFAULT_SLEEP_TIME = 60
ERROR_SLEEP_TIME = 2


async def sleep_for_429(response: ClientResponse):
    """
    Sleep for handling 429 - Too many requests response.
    :param response: http response object
    :param err: aiohttp response error
    :return: None
    """
    await asyncio.sleep(DEFAULT_SLEEP_TIME)


async def handle_callback(callback, text, response, session):
    if not callback:
        return
    # call callback function and handle async callback functions
    callback_function = callback(text, response, session)
    if isawaitable(callback_function):
        await callback(text, response, session)


async def async_http_request(session: ClientSession, should_run_event=None, handle_429=sleep_for_429,
                             max_retries=MAX_RETRIES,
                             retry_on_error=False,
                             retry_sleep_time=ERROR_SLEEP_TIME,
                             callback=None, **kwargs):
    """
    Makes an async request
    :param max_retries: max retries number
    :param retry_sleep_time: sleep time on  error (seconds)
    :param retry_on_error: if true, async request will sleep retry_sleep_time on connection refused error and then
                            retry 'max_retries' times.
    :param should_run_event: async event - determine if we need to wait before the request.
    :param handle_429: function for handling 429 errors
    :param session: the session object
    :param callback: callback function to be called after the http request.
                     callback function should be:
                     callback(response_text: str, response: aiohttp.ClientResponse, session: Clientsession)
                     callback may be an async function (good practice) or a sync function.
    :param kwargs: all parameters to session.request, e.g. {method: "get", "url": "..",
                                                            params={'q1': 'a1'}, headers={}}
                   more: https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request

    notes: should_run_event is an asyncio event object that determines if we should wait before running the request.
            asyncio event will wait on event.wait() until event.set() is called. so we always starts with event.set()
            if there is a 429 response, we clear() the event, wait for handle_429 function to run
            (all the other coroutines will block on wait() on this step) and then set() it again.
            in this way a single 429 response will block all the other running requests from flooding the server.
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
    retries = 0
    # Send the request
    while retries < max_retries:
        try:
            if should_run_event is not None:
                await should_run_event.wait()
            async with session.request(**kwargs) as response:
                if get_binary is True:
                    binary_response = await response.read()
                    return binary_response, response

                text = await response.text()
                if response.status == 429 and should_run_event is not None:
                    logger.debug('Handling 429 response')
                    if should_run_event.is_set():
                        should_run_event.clear()
                        logger.debug('Calling handling 429 function')
                        await handle_429(response)
                        should_run_event.set()
                else:
                    await handle_callback(callback, text, response, session)
                    return text, response
        except ClientConnectorError as e:
            if not retry_on_error:
                raise e
            logger.warning(f'Got error on http request, retry: {retries}')
            if retries == MAX_RETRIES:
                logger.error('Max retries exceeded for async request')
                raise e
            if should_run_event is not None and should_run_event.is_set():
                should_run_event.clear()
                await asyncio.sleep(retry_sleep_time)
                should_run_event.set()
        retries += 1


async def run(reqs, handle_429_function, max_retries=MAX_RETRIES,
              retry_on_error=False,
              retry_sleep_time=ERROR_SLEEP_TIME,  **kwargs):
    tasks = []
    # Fetch all responses within one Client session,
    # keep connection alive for all requests.A
    ssl_ctx = None
    if kwargs.get('cert') is not None:
        cert = kwargs.get('cert')
        ssl_ctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(*cert)
    connector = TCPConnector(limit=None, ssl_context=ssl_ctx)
    should_run_event = asyncio.Event()
    should_run_event.set()
    async with ClientSession(connector=connector) as session:
        for req in reqs:
            task = asyncio.ensure_future(async_http_request(session, should_run_event,
                                                            handle_429=handle_429_function,
                                                            max_retries=max_retries,
                                                            retry_on_error=retry_on_error,
                                                            retry_sleep_time=retry_sleep_time,
                                                            **req))
            tasks.append(task)

        # return_exceptions=True means that we don't propogate exceptions up, we just return all exceptions as
        # the result of the requests.
        # so the result can be ["first_result", "second_result", Exception(...), "fourth_result"]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
    connector.close()
    return responses


def async_request(req_list: list, handle_429_function=sleep_for_429,
                  max_retries=MAX_RETRIES,
                  retry_on_error=False,
                  retry_sleep_time=ERROR_SLEEP_TIME, **kwargs) -> typing.List[ClientResponse]:
    """
    Makes requests
    :param max_retries: max retries number
    :param retry_sleep_time: sleep time on  error (seconds)
    :param retry_on_error: if true, async request will sleep retry_sleep_time on connection refused error and then
                            retry 'max_retries' times.
    :param handle_429_function:
    :param req_list: a list of dict for making a request.
    :return: a list of aio.ClientResponse. If an exception occurs, the output of it will be an Exception object.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    future = asyncio.ensure_future(run(req_list, handle_429_function, max_retries=max_retries,
                                       retry_on_error=retry_on_error,
                                       retry_sleep_time=retry_sleep_time, **kwargs))
    result = loop.run_until_complete(future)
    # Wait 250 ms for the underlying SSL connections to close
    # https://aiohttp.readthedocs.io/en/stable/client_advanced.html
    loop.run_until_complete(asyncio.sleep(0.250))
    return result
