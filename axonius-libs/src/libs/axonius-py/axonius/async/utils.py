"""
Async io utilities.
"""
import asyncio
import typing
from aiohttp import ClientSession, ClientTimeout, ClientResponse, BasicAuth


def async_request(req_list: list) -> typing.List[ClientResponse]:
    """
    Makes requests
    :param req_list: a list of dict for making a request.
    :return: a list of aio.ClientResponse. If an exception occurs, the output of it will be an Exception object.
    """
    async def request(session: ClientSession, **kwargs):
        """
        Makes an async request
        :param session: the session object
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
            return text, response

    async def run(reqs):
        tasks = []

        # Fetch all responses within one Client session,
        # keep connection alive for all requests.
        async with ClientSession() as session:
            for req in reqs:
                task = asyncio.ensure_future(request(session, **req))
                tasks.append(task)

            # return_exceptions=True means that we don't propogate exceptions up, we just return all exceptions as
            # the result of the requests.
            # so the result can be ["first_result", "second_result", Exception(...), "fourth_result"]
            return await asyncio.gather(*tasks, return_exceptions=True)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    future = asyncio.ensure_future(run(req_list))
    return loop.run_until_complete(future)
