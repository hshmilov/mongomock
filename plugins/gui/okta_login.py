import calendar
from datetime import datetime, timedelta
from threading import RLock

import jose
import requests

from axonius.utils.revving_cache import rev_cached
from dataclasses import dataclass, field
from flask import request
from jose import jws, jwt
import logging

from axonius.plugin_base import PluginBase

public_key_cache = {}

logger = logging.getLogger(f'axonius.{__name__}')


def make_okta_api_request(resource, method='get'):
    okta_config = PluginBase.Instance._okta
    url = okta_config['url']
    url = f'{url}/api{resource}'

    return requests.request(method, url, headers={
        'Accept': 'application/json',
        'Authorization': okta_config['api_token']
    })


def get_oauth_url(resource: str = '') -> str:
    """
    Gets the base URL for oauth requests
    """
    okta_config = PluginBase.Instance._okta
    url = okta_config['url']
    authorization_server = okta_config.get('authorization_server')
    if okta_config.get('authorization_server', False):
        return f'{url}/oauth2/{authorization_server}{resource}'
    return f"{okta_config['url']}/oauth2/{resource}"


def okta_post(resource: str, data: dict) -> requests.Response:
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    return requests.post(get_oauth_url(resource),
                         data=data,
                         headers=headers)


def okta_post_authenticated(resource: str, data: dict) -> requests.Response:
    okta_config = PluginBase.Instance._okta

    return okta_post(resource, {
        **{
            'client_id': okta_config['client_id'],
            'client_secret': okta_config['client_secret'],
        }, **data
    })


@dataclass()
class OidcData:
    # id token
    id_token: str
    # The jwt claims
    claims: object
    # The access token
    access_token: str
    # The refresh token
    refresh_token: str
    # The main lock
    lock: RLock = field(default_factory=RLock)

    def beautify(self) -> dict:
        """
        Returns the data that could be directed to the frontend user
        :raises: Various exceptions if the token fails the refresh, TBD the exceptions themselves
        """
        with self.lock:
            return {
                'id_token': self.id_token,
                'claims': self.claims,
            }


def fetch_jwk_for(id_token):
    """
    Get's the JSON web key from the given ID token;
    >>this is code from Okta's example on how to implement Okta in flask<<
    """
    if id_token is None:
        raise NameError('id_token is required')

    unverified_header = jws.get_unverified_header(id_token)
    if 'kid' in unverified_header:
        key_id = unverified_header['kid']
    else:
        raise ValueError('The id_token header must contain a "kid"')
    if key_id in public_key_cache:
        return public_key_cache[key_id]

    r = requests.get(get_oauth_url('/v1/keys'))
    jwks = r.json()
    for key in jwks['keys']:
        jwk_id = key['kid']
        public_key_cache[jwk_id] = key

    if key_id in public_key_cache:
        return public_key_cache[key_id]
    else:
        raise RuntimeError("Unable to fetch public key from jwks_uri")


def try_connecting_using_okta(okta_config) -> OidcData:
    """
    Verifies that the request is indeed a redirected request from okta.
    If the request is valid returns an OidcData, otherwise None
    """
    if not okta_config.get('enabled') is True:
        return None
    cookies = request.cookies
    if 'okta-oauth-nonce' in cookies and 'okta-oauth-state' in cookies:
        nonce = cookies['okta-oauth-nonce']
        state = cookies['okta-oauth-state']
    else:
        logger.info("No okta cookies")
        return None

    if request.args.get('state') != state:
        logger.info("No state")
        return None

    gui2_url = okta_config['gui2_url']
    if gui2_url.endswith('/'):
        gui2_url = gui2_url[:-1]
    querystring = {
        'grant_type': 'authorization_code',
        'code': request.args.get('code'),
        'redirect_uri': f'{gui2_url}/api/okta-redirect',
        'client_secret': okta_config['client_secret'],
        'client_id': okta_config['client_id'],
    }

    return_value = okta_post('/v1/token', querystring).json()
    if 'id_token' not in return_value or 'access_token' not in return_value:
        logger.info("No ID token")
        return None

    id_token = return_value['id_token']
    access_token = return_value['access_token']
    refresh_token = return_value.get('refresh_token')

    leeway = 60 * 5  # 5 minutes

    if not okta_config.get('authorization_server', False):
        issuer = okta_config['url']
    else:
        issuer = get_oauth_url()

    jwt_kwargs = {
        'algorithms': 'RS256',
        'options': {
            'verify_at_hash': False,
            # Used for leeway on the "exp" claim
            'leeway': leeway
        },
        'issuer': issuer,
        'audience': okta_config['client_id'],
        'access_token': access_token
    }

    try:
        jwks_with_public_key = fetch_jwk_for(id_token)
        logger.info(id_token)
        logger.info(jwks_with_public_key)
        logger.info(jwt_kwargs)
        claims = jwt.decode(
            id_token,
            jwks_with_public_key,
            **jwt_kwargs)

    except (jose.exceptions.JWTClaimsError,
            jose.exceptions.JWTError,
            jose.exceptions.JWSError,
            jose.exceptions.ExpiredSignatureError,
            NameError,
            ValueError):
        logger.exception("err validating jwt")
        return None
    if nonce != claims['nonce']:
        logger.info("Nonce isn't true")
        return None

    time_now_with_leeway = datetime.utcnow() + timedelta(seconds=leeway)
    acceptable_iat = calendar.timegm(time_now_with_leeway.timetuple())
    if 'iat' in claims and claims['iat'] > acceptable_iat:
        logger.info("IAT isn't true")
        return None

    oidc_data = OidcData(id_token, claims, access_token, refresh_token)
    return oidc_data
