import logging
logger = logging.getLogger(f"axonius.{__name__}")
import xml.etree.ElementTree as ET
import math
from axonius.clients.rest.exception import RESTException
from axonius.clients.rest.connection import RESTConnection
from axonius.async.utils import async_request


AIO_CHUNKS = 50


class BigfixConnection(RESTConnection):

    def _connect(self):

        if self._username is not None and self._password is not None:
            self._get("computers", do_basic_auth=True, use_json_in_response=False)
        else:
            raise RESTException("No user name or password")

    def get_device_list(self, **kwargs):
        xml_computers = ET.fromstring(self._get("computers", use_json_in_response=False))
        req_list = []
        for computer_node in xml_computers:
            try:
                if computer_node.tag == 'Computer':
                    computer_resource = computer_node.attrib.get('Resource')
                    if computer_resource:
                        aioreq_dict = {
                            "url": computer_resource,
                            "method": "get",
                            "auth": (self._username, self._password),
                            "timeout": self._session_timeout,
                            "headers": self._permanent_headers.copy(),
                        }
                        if self._verify_ssl is False:
                            aioreq_dict["ssl"] = False

                        if self._proxies.get('https') is not None:
                            aioreq_dict['proxy'] = self._proxies['https']
                        elif self._proxies.get('http') is not None:
                            aioreq_dict['proxy'] = self._proxies['http']

                        req_list.append(aioreq_dict)
            except Exception:
                logger.exception(f"can't parse computer node {str(computer_node)}, not adding it to async requests")

        # Go over all requests, if there is an exception just log it but don't yield it. Exceptions
        # occur, for example, on network problems.
        # We have to make chunks here, or else - if there are 10,000 devices, we will request 10,000 times in parallel,
        # which is really bad.

        for chunk_id in range(int(math.ceil(len(req_list) / AIO_CHUNKS))):
            try:
                all_answers = async_request(req_list[AIO_CHUNKS * chunk_id: AIO_CHUNKS * (chunk_id + 1)])
                logger.info(f"Parsing {(AIO_CHUNKS * chunk_id) + len(all_answers)} answers out of {len(req_list)}")

                for response in all_answers:
                    try:
                        if not isinstance(response, Exception):
                            text, response_object = response
                            response_object.raise_for_status()
                            yield text
                        else:
                            logger.error(f"Returned an exception instead of async response, its {response}")
                    except Exception:
                        logger.exception(f"Problem parsing response")
            except Exception:
                logger.exception(f"Problem parsing a chunk of async requests")
