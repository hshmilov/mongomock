import sys
import time
import logging
import multiprocessing

try:
    import requests
except ImportError:
    print('requests module is not available')
    raise

"""
SSLLabs fetch library
https://github.com/ssllabs/ssllabs-scan

Fetch ssl certificates data using qualys ssllabs api.
"""
__version__ = '1.3'
__author__ = 'takeshix@adversec.com'
__license__ = 'Apache 2.0'
__all__ = ['SSLLabsAssessment']

logger = logging.getLogger()


class AccessProblem(Exception):
    pass


class SSLLabsAssessment(object):
    """A basic API interface which eases the
    creation of SSL Labs assessments.

    See the *analyze* function for more information.

    Note: This module defaults to the SSL Labs dev
    API in favour of advanced features like IPv6
    support. Beware, this might change in future
    releases. See the following documentation sources
    for further information:

    * dev: https://github.com/ssllabs/ssllabs-scan/blob/master/ssllabs-api-docs.md
    * stable: https://github.com/ssllabs/ssllabs-scan/blob/stable/ssllabs-api-docs.md
    """
    API_URLS = [
        'https://api.dev.ssllabs.com/api/v3/',  # dev
        'https://api.ssllabs.com/api/v3/'      # stable
    ]
    API_URL = None
    MAX_ASSESSMENTS = 25
    CLIENT_MAX_ASSESSMENTS = 25
    CURRENT_ASSESSMENTS = 0

    def __init__(self, host=None, api_url=None, proxy=None, *args, **kwargs):
        if host:
            self.host = host
        if api_url:
            self.API_URL = api_url
        self.manager = multiprocessing.Manager()
        self.endpoint_jobs = []
        self.publish = None
        self.start_new = None
        self.return_all = None
        self.from_cache = None
        self.max_age = None
        self.proxies = {'https': proxy} if proxy else {}
        self.ignore_mismatch = None

    def set_host(self, host):
        """Set the target FQDN.

        This public function can be used to
        set the target FQDN after the object
        has already been initialized.
        """
        self.host = host

    @staticmethod
    def _die_on_error(msg):
        if msg:
            logger.error(msg)
        raise AccessProblem(msg)

    def _handle_api_error(self, response):
        _status = response.status_code
        if _status == 200:
            logger.debug('API return: %s', response.json())
            return response
        error_message = '; '.join('{}{}{}'.format(
            error.get('field') or '', ': ' if error.get('field') else '',
            error.get('message') or 'Unknown error')
            for error in response.json().get('errors') or ()) \
            or response.text
        if _status == 400:
            self._die_on_error('[API] invocation error: {}'.format(error_message))
        elif _status == 429:
            self._die_on_error('[API] client request rate too high or too many new'
                               'assessments too fast: {}'.format(error_message))
        elif _status == 500:
            self._die_on_error('[API] internal error: {}'.format(error_message))
        elif _status == 503:
            self._die_on_error('[API] the service is not available: {}'.format(error_message))
        elif _status == 529:
            self._die_on_error('[API] the service is overloaded: {}'.format(error_message))
        else:
            self._die_on_error('[API] unknown status code: {}, {}'.format(_status, error_message))

    def _check_api_info(self):
        try:
            if not self.API_URL:
                for url in self.API_URLS:
                    try:
                        response = self._handle_api_error(requests.get('{}info'.format(url), proxies=self.proxies,
                                                                       verify=False)).json()
                        self.API_URL = url
                        break
                    except requests.ConnectionError:
                        continue
            else:
                try:
                    response = self._handle_api_error(requests.get('{}info'.format(self.API_URL),
                                                                   proxies=self.proxies, verify=False)).json()
                except requests.ConnectionError:
                    self._die_on_error('[ERROR] Provided API URL is unavailable.')

            if not self.API_URL:
                self._die_on_error('[ERROR] SSL Labs APIs are down. Please try again later.')

            self.CLIENT_MAX_ASSESSMENTS = response.get('clientMaxAssessments')
            self.CURRENT_ASSESSMENTS = response.get('currentAssessments')
            self.MAX_ASSESSMENTS = response.get('maxAssessments')
            if self.MAX_ASSESSMENTS <= 0:
                logger.debug('Rate limit reached')
                return False
            logger.info('[NOTICE] SSL Labs v{engine_version} (criteria version '
                        '{criteria_version})'.format(
                            engine_version=response.get('engineVersion'),
                            criteria_version=response.get('criteriaVersion')))
            logger.info('[NOTICE] {server_message}'.format(
                server_message=response.get('messages')[0]))
            return True
        except AccessProblem as e:
            raise
        except Exception as e:
            logger.exception(e)
            return False

    def _trigger_new_assessment(self):
        _url = '{api_url}analyze?host={host}&publish={publish}&ignoreMismatch={ignore_mismatch}&all={return_all}'
        _url = _url.format(
            api_url=self.API_URL,
            host=self.host,
            publish=self.publish,
            ignore_mismatch=self.ignore_mismatch,
            return_all=self.return_all)
        if self.from_cache == 'on':
            _url += '&fromCache={from_cache}&maxAge={max_age}'
            _url = _url.format(
                from_cache=self.from_cache,
                max_age=self.max_age)
        else:
            _url += '&startNew=on'
        try:
            return self._handle_api_error(requests.get(_url, proxies=self.proxies, verify=False)).json()
        except AccessProblem as e:
            raise
        except Exception as e:
            logger.exception(e)
            return {}

    def _poll_api(self):
        _url = '{api_url}analyze?host={host}&publish={publish}&ignoreMismatch={ignore_mismatch}&all={return_all}'
        _url = _url.format(
            api_url=self.API_URL,
            host=self.host,
            publish=self.publish,
            ignore_mismatch=self.ignore_mismatch,
            return_all=self.return_all)
        if self.from_cache == 'on':
            _url += '&fromCache={from_cache}&maxAge={max_age}'
            _url = _url.format(
                from_cache=self.from_cache,
                max_age=self.max_age)
        try:
            return self._handle_api_error(requests.get(_url, proxies=self.proxies, verify=False)).json()
        except AccessProblem as e:
            raise
        except Exception as e:
            logger.exception(e)
            return {}

    def _get_all_results(self):
        logger.debug('Requesting full results')
        _url = '{api_url}analyze?host={host}&publish={publish}&ignoreMismatch={ignore_mismatch}&all={return_all}'
        _url = _url.format(
            api_url=self.API_URL,
            host=self.host,
            publish=self.publish,
            ignore_mismatch=self.ignore_mismatch,
            return_all=self.return_all)
        if self.from_cache == 'on':
            _url += '&fromCache={from_cache}&maxAge={max_age}'
            _url = _url.format(
                from_cache=self.from_cache,
                max_age=self.max_age)
        try:
            return self._handle_api_error(requests.get(_url, proxies=self.proxies, verify=False)).json()
        except AccessProblem as e:
            raise
        except Exception as e:
            logger.exception(e)
            return False

    def _get_detailed_endpoint_information(self, host, ip, from_cache='off'):
        logger.debug('Getting detailed endpoint information')
        url = '{api_url}getEndpointData?host={host}&s={endpoint_ip}&fromCache={from_cache}'.format(
            api_url=self.API_URL,
            host=host,
            endpoint_ip=ip,
            from_cache=from_cache)
        while True:
            try:
                response = self._handle_api_error(requests.get(url, proxies=self.proxies, verify=False)).json()
                logger.info('[{ip_address}] Progress: {progress}%, Status: {status}'.format(
                    ip_address=response.get('ipAddress'),
                    progress='{}'.format(response.get('progress')) if response.get('progress') > -1 else '0',
                    status=response.get('statusDetailsMessage')))
                if response.get('progress') == 100:
                    return
                elif response.get('progress') < 0:
                    time.sleep(10)
                else:
                    time.sleep(5)
            except KeyboardInterrupt:
                return
            except AccessProblem as e:
                raise
            except Exception as e:
                logger.exception(e)
                time.sleep(5)
                continue

    def analyze(self, host=None, publish='off', start_new='on',
                from_cache='off', max_age=5, return_all='done',
                ignore_mismatch='on', resume=False, detail=False):
        """Start the assessment process.

        This is basically a wrapper function
        for all the API communication which
        takes care of everything. Any non-default
        behaviour of assessment processes can be
        tweaked with arguments to this function.

        Providing a *host* containing the FQDN of
        the target system(s) is the only mandatory
        argument. All remaining arguments are
        optional.
        """
        if not self._check_api_info():
            return False

        if host:
            self.host = host
        elif not self.host:
            return False

        self.publish = publish
        self.start_new = start_new
        self.from_cache = from_cache
        self.max_age = max_age
        self.return_all = return_all
        self.ignore_mismatch = ignore_mismatch
        if not resume:
            logger.info('Retrieving assessment for {}...'.format(self.host))
            _status = self._trigger_new_assessment()
            if not _status:
                return False
            if _status.get('status') == 'READY':
                if self.return_all in ('on', 'done'):
                    return _status
            elif _status.get('status') == 'ERROR':
                logger.error('An error occured: {}'.format(_status.get('statusMessage')))
                return
        else:
            logger.info('Checking running assessment for {}'.format(self.host))
        while True:
            _status = self._poll_api()
            if not _status:
                logger.debug('Poll failed')
                break
            if _status.get('status') == 'IN_PROGRESS':
                if resume:
                    logger.info('Assessment is still in progress')
                break
            elif _status.get('status') == 'READY':
                if resume:
                    logger.info('No running assessment. Use --use-cache '
                                'to receive a cached assessment, or start a new one.')
                    return
                else:
                    return _status if self.return_all in ('on', 'done') else self._get_all_results()
            elif _status.get('status') == 'ERROR':
                logger.error('An error occured: {}'.format(_status.get('statusMessage')))
                return
            else:
                continue
        if _status.get('endpoints'):
            logger.debug('Testing {} host(s)'.format(len(_status.get('endpoints'))))
        try:
            if detail:
                for endpoint in _status.get('endpoints', []):
                    _process = multiprocessing.Process(
                        target=self._get_detailed_endpoint_information,
                        args=(self.host, endpoint.get('ipAddress')))
                    self.endpoint_jobs.append(_process)
                    _process.start()
                for job in self.endpoint_jobs:
                    job.join()
            while True:
                _status = self._poll_api()
                if not _status:
                    break
                _host_status = _status.get('status')
                if _host_status == 'IN_PROGRESS':
                    if logging.getLogger().getEffectiveLevel() <= 20:
                        sys.stdout.write('.')
                        sys.stdout.flush()
                    time.sleep(10)
                elif _host_status == 'READY':
                    return _status if self.return_all in ('on', 'done') else self._get_all_results()
                elif _host_status == 'ERROR':
                    logger.error('[ERROR] An error occured: {}'.format(_status.get('statusMessage')))
                    return
                elif _host_status == 'DNS':
                    logger.debug('Resolving hostname')
                    time.sleep(4)
                else:
                    logger.info('Unknown host status: {}'.format(_host_status))
        except KeyboardInterrupt:
            pass
        except AccessProblem as e:
            raise
        except Exception as e:
            logger.exception(e)
            return
