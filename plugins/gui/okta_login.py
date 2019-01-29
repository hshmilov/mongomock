import calendar
from datetime import datetime, timedelta

import jose
import requests
from flask import request, session
from jose import jws, jwt
import logging

public_key_cache = {}

logger = logging.getLogger(f'axonius.{__name__}')


def fetch_jwk_for(okta_config, id_token=None):
    """
    Get's the JSON web key from the given ID token;
    >>this is code from Okta's example on how to implement Okta in flask<<
    """
    if id_token is None:
        raise NameError('id_token is required')

    jwks_uri = f"{okta_config['url']}/oauth2/default/v1/keys"

    unverified_header = jws.get_unverified_header(id_token)
    if 'kid' in unverified_header:
        key_id = unverified_header['kid']
    else:
        raise ValueError('The id_token header must contain a "kid"')
    if key_id in public_key_cache:
        return public_key_cache[key_id]

    r = requests.get(jwks_uri)
    jwks = r.json()
    for key in jwks['keys']:
        jwk_id = key['kid']
        public_key_cache[jwk_id] = key

    if key_id in public_key_cache:
        return public_key_cache[key_id]
    else:
        raise RuntimeError("Unable to fetch public key from jwks_uri")


def try_connecting_using_okta(okta_config) -> bool:
    """
    Verifies that the request is indeed a redirected request from okta.
    If the request is valid, assigns the session to mark the user as logged in.
    >>this is code from Okta's example on how to implement Okta in flask<<
    :return: whether or not the request is legit
    """
    if not okta_config.get('enabled') is True:
        return
    cookies = request.cookies
    if 'okta-oauth-nonce' in cookies and 'okta-oauth-state' in cookies:
        nonce = cookies['okta-oauth-nonce']
        state = cookies['okta-oauth-state']
    else:
        logger.info("No okta cookies")
        return False

    if request.args.get('state') != state:
        logger.info("No state")
        return False

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

    url = f"{okta_config['url']}/oauth2/default/v1/token"

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    r = requests.post(url,
                      data=querystring,
                      # auth=auth,
                      headers=headers)
    return_value = r.json()
    if 'id_token' not in return_value:
        logger.info("No ID token")
        return False
    id_token = return_value['id_token']
    five_minutes_in_seconds = 300
    leeway = five_minutes_in_seconds
    jwt_kwargs = {
        'algorithms': 'RS256',
        'options': {
            'verify_at_hash': False,
            # Used for leeway on the "exp" claim
            'leeway': leeway
        },
        'issuer': f'{okta_config["url"]}/oauth2/default',
        'audience': okta_config['client_id']
    }
    if 'access_token' in return_value:
        jwt_kwargs['access_token'] = return_value['access_token']
    try:
        jwks_with_public_key = fetch_jwk_for(okta_config, id_token)
        claims = jwt.decode(
            id_token,
            jwks_with_public_key,
            **jwt_kwargs)

    except (jose.exceptions.JWTClaimsError,
            jose.exceptions.JWTError,
            jose.exceptions.JWSError,
            jose.exceptions.ExpiredSignatureError,
            NameError,
            ValueError) as err:
        logger.exception("err")
        return False
    if nonce != claims['nonce']:
        logger.info("Nonce isn't true")
        return False
    time_now_with_leeway = datetime.utcnow() + timedelta(seconds=leeway)
    acceptable_iat = calendar.timegm(time_now_with_leeway.timetuple())
    if 'iat' in claims and claims['iat'] > acceptable_iat:
        logger.info("IAT isn't true")
        return False
    session['id_token'] = id_token
    return claims
