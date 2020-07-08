# pylint: disable=too-many-lines
import logging
from re import match

from aws_adapter.connection.structures import AWSDeviceAdapter, AWSCloudfrontCookie, \
    AWSCloudfrontForwardedValues, AWSCloudfrontActiveTrustedSigners, \
    AWSCloudfrontTrustedSigners, AWSCloudfrontLambdaAssociations, \
    AWSCloudfrontCacheBehavior, AWSCustomHeaders, AWSCloudfrontOriginGroups, \
    AWSCloudfrontCustomOriginConfig, AWSCloudfrontOrigins, \
    AWSCloudfrontCustomErrors, AWSCloudfrontLoggingConfig, \
    AWSCloudfrontViewerCertificate, AWSCloudfrontRestriction, \
    AWSCloudfrontDistributionConfig, AWSCloudfrontAliasRecordals, \
    AWSCloudfrontDistribution, AWSCloudfrontTrustedSignersDetails
from aws_adapter.consts import FORWARDED_COOKIES, VIEWER_PROTOCOL_POLICY, \
    PROTOCOL_POLICY, SSL_SUPPORT_METHOD, MINIMUM_PROTOCOL_VERSION, \
    CERTIFICATE_SOURCE, CLOUDFRONT_RESTRICTION_TYPE, PRICE_CLASS, \
    HTTP_VERSION, ALIAS_RECORDALS_STATUS, ARN_PATTERN

from axonius.utils.datetime import parse_date

logger = logging.getLogger(f'axonius.{__name__}')


def parse_int(value):
    try:
        if value is not None:
            return int(value)
    except Exception as e:
        if value is not None:
            logger.warning(f'Failed to parse {value} as int: {str(e)}')
    return None


def parse_bool(value):
    # pylint: disable=no-else-return
    if value and isinstance(value, (bool, int)):
        return bool(value)
    elif value and isinstance(value, str):
        return value.lower() in ('true', 'yes')
    return None


def query_active_trusted_signers(signers: dict, arn: str) -> dict:
    active_signers = dict()
    active_signers['enabled'] = signers.get('Enabled')
    active_signers['items'] = list()

    try:  # pylint: disable=too-many-nested-blocks
        for item in signers.get('Items') or []:
            if item and isinstance(item, dict):
                item_dict = dict()
                account_number = item.get('AwsAccountNumber')
                if account_number and isinstance(account_number, str):
                    if account_number == 'self':
                        # extract the aws account number to not display 'self'
                        try:
                            result = match(ARN_PATTERN, arn)
                            account_number = result.group(4)
                        except Exception:
                            logger.exception(f'Unable to extract the account '
                                             f'number from the ARN: '
                                             f'{str(account_number)}')
                            continue
                    item_dict['account_number'] = account_number
                else:
                    if account_number is not None:
                        logger.warning(
                            f'Malformed AWS account number. Expected a '
                            f'str, got {type(account_number)}:'
                            f'{str(account_number)}')

                keypair_ids = item.get('KeyPairIds')
                if keypair_ids and isinstance(keypair_ids, dict):
                    item_dict['keypair_ids'] = keypair_ids.get('Items') or []
                else:
                    if keypair_ids is not None:
                        logger.warning(
                            f'Malformed keypair IDs. Expected a dict, '
                            f'got {type(keypair_ids)}: {str(keypair_ids)}')

                active_signers['items'].append(item_dict)
            else:
                if item is not None:
                    logger.warning(f'Malformed trusted signers item. Expected '
                                   f'a dict, got {type(item)}: {str(item)}')
                continue
    except Exception:
        logger.exception(f'Unable to query active trusted signers items: '
                         f'{str(signers.get("Items"))}')

    return active_signers


def query_distribution_config(config: dict, arn: str) -> dict:
    # pylint: disable=too-many-branches, too-many-statements
    dist_config = dict()

    dist_config['caller_reference'] = config.get('CallerReference')
    dist_config['comment'] = config.get('Comment')
    dist_config['default_root_object'] = config.get('DefaultRootObject')
    dist_config['price_class'] = config.get('PriceClass')
    dist_config['enabled'] = config.get('Enabled')
    dist_config['web_acl_id'] = config.get('WebACLId')
    dist_config['http_version'] = config.get('HttpVersion')
    dist_config['ipv6_enabled'] = config.get('IsIPV6Enabled')

    try:
        aliases = config.get('Aliases')
        if aliases and isinstance(aliases, dict):
            dist_config['aliases'] = aliases.get('Items') or []
        else:
            if aliases is not None:
                logger.warning(f'Malformed aliases. Expected a dict, got '
                               f'{type(aliases)}: {str(aliases)}')
    except Exception:
        logger.exception(f'Unable to query Cloudfront distro configuration '
                         f'aliases: {str(config.get("Aliases"))}')

    # origins
    try:  # pylint: disable=too-many-nested-blocks
        origins = config.get('Origins')
        dist_config['domains'] = list()
        if origins and isinstance(origins, dict):
            dist_config['origins'] = query_origins(origins)
            if isinstance(dist_config.get('origins'), list):
                domains = set()
                for origin in dist_config.get('origins'):
                    if isinstance(origin, dict):
                        domain = origin.get('domain_name')
                        if domain and isinstance(domain, str):
                            try:
                                # extracting the constant domain name (domain
                                # includes aws routing info that we don't need
                                domains.add(domain.split('.')[0])
                            except Exception:
                                logger.exception(
                                    f'Unable to extract domains from '
                                    f'origins: {str(domains)}')
                        else:
                            if domain is not None:
                                logger.warning(
                                    f'Malformed domain. Expected a str, got '
                                    f'{type(domain)}: {str(domain)}')
                    else:
                        if origin is not None:
                            logger.warning(
                                f'Malformed distro config origin. Expected a '
                                f'dict, got {type(origin)}: {str(origin)}')

                dist_config['domains'] = list(domains)
            else:
                if dist_config is not None:
                    logger.warning(
                        f'Malformed distribution configuration. Expected '
                        f'a list, got {type(dist_config)}:'
                        f'{str(dist_config)}')
        else:
            if origins is not None:
                logger.warning(f'Malformed origins. Expected a dict, got '
                               f'{type(origins)}: {str(origins)}')
    except Exception:
        logger.exception(f'Unable to query Cloudfront distro configuration '
                         f'origins: {str(config.get("Origins"))}')

    # origin groups
    try:
        origin_groups = config.get('OriginGroups')
        dist_config['origin_groups'] = list()
        if origin_groups and isinstance(origin_groups, dict):
            dist_config['origin_groups'] = query_origin_groups(origin_groups)
        else:
            if origin_groups is not None:
                logger.warning(f'Malformed origin groups. Expected a dict, got '
                               f'{type(origin_groups)}: {str(origin_groups)}')
    except Exception:
        logger.exception(f'Unable to query Cloudfront distro configuration '
                         f'origin groups: {str(config.get("OriginGroups"))}')

    # default cache behavior
    try:
        default_behaviors = config.get('DefaultCacheBehavior')
        dist_config['default_cache_behaviors'] = dict()
        if default_behaviors and isinstance(default_behaviors, dict):
            dist_config['default_cache_behaviors'] = query_default_cache_behaviors(
                default_behaviors=default_behaviors,
                arn=arn)
        else:
            if default_behaviors is not None:
                logger.warning(f'Malformed default cache behaviors. Expected a '
                               f'dict, got {type(default_behaviors)}: '
                               f'{str(default_behaviors)}')
    except Exception:
        logger.exception(f'Unable to query Cloudfront distro configuration '
                         f'default cache behavior: '
                         f'{str(config.get("DefaultCacheBehavior"))}')

    # cache behaviors
    try:
        cache_behaviors = config.get('CacheBehaviors')
        dist_config['cache_behaviors'] = dict()
        if cache_behaviors and isinstance(cache_behaviors, dict):
            dist_config['cache_behaviors'] = query_cache_behaviors(
                cache_behaviors=cache_behaviors,
                arn=arn)
        else:
            if cache_behaviors is not None:
                logger.warning(f'Malformed cache behaviors. Expected a dict, '
                               f'got {type(cache_behaviors)}: '
                               f'{str(cache_behaviors)}')
    except Exception:
        logger.exception(f'Unable to query Cloudfront distro configuration '
                         f'cache behaviors: '
                         f'{str(config.get("CacheBehaviors"))}')

    # custom error responses
    try:
        custom_error_responses = config.get('CustomErrorResponses')
        dist_config['custom_error_responses'] = list()
        if custom_error_responses and isinstance(custom_error_responses, dict):
            dist_config['custom_error_responses'] = query_custom_error_responses(
                custom_error_responses)
        else:
            if custom_error_responses is not None:
                logger.warning(f'Malformed custom error responses. Expected a '
                               f'dict, got {type(custom_error_responses)}: '
                               f'{str(custom_error_responses)}')
    except Exception:
        logger.exception(f'Unable to query Cloudfront distro configuration '
                         f'custom error responses: '
                         f'{str(config.get("CustomErrorResponses"))}')

    # logging
    try:
        logging_config = config.get('Logging')
        dist_config['logging'] = dict()
        if logging_config and isinstance(logging_config, dict):
            dist_config['logging'] = query_logging(logging_config)
        else:
            if logging_config is not None:
                logger.warning(
                    f'Malformed logging configuration. Expected a dict, '
                    f'got {type(logging_config)}: {str(logging_config)}')
    except Exception:
        logger.exception(f'Unable to query Cloudfront distro configuration '
                         f'logging: {str(config.get("Logging"))}')

    # viewer certificate
    try:
        certificate = config.get('ViewerCertificate')
        dist_config['viewer_certificate'] = dict()
        if certificate and isinstance(certificate, dict):
            dist_config['viewer_certificate'] = query_viewer_certificate(certificate)
        else:
            if certificate is not None:
                logger.warning(f'Malformed certificate. Expected a dict, got '
                               f'{type(certificate)}: {str(certificate)}')
    except Exception:
        logger.exception(f'Unable to query Cloudfront distro configuration '
                         f'viewer certificate: '
                         f'{str(config.get("ViewerCertificate"))}')

    # restrictions
    try:
        restrictions = config.get('Restrictions')
        dist_config['restrictions'] = dict()
        if restrictions and isinstance(restrictions, dict):
            dist_config['restrictions'] = query_restrictions(restrictions)
        else:
            if restrictions is not None:
                logger.warning(f'Malformed restrictions. Expected a dict, got '
                               f'{type(restrictions)}: {str(restrictions)}')
    except Exception:
        logger.exception(f'Unable to query Cloudfront distro configuration '
                         f'restrictions: {str(config.get("Restrictions"))}')

    return dist_config


def query_restrictions(restrictions: dict) -> dict:
    restriction_config = dict()

    restriction = restrictions.get('GeoRestriction')
    if restriction and isinstance(restriction, dict):
        restriction_config['restriction_type'] = restriction.get('RestrictionType')
        restriction_config['restrictions'] = restriction.get('Items') or []
    else:
        if restriction is not None:
            logger.warning(f'Malformed geo-restriction. Expected a dict, got '
                           f'{type(restriction)}: {str(restriction)}')

    return restriction_config


def query_viewer_certificate(certificate: dict) -> dict:
    cert_config = dict()
    cert_config['default_certificate'] = certificate.get('CloudFrontDefaultCertificate')
    cert_config['iam_certificate_id'] = certificate.get('IAMCertificateId')
    cert_config['acm_certificate_arn'] = certificate.get('ACMCertificateArn')
    cert_config['ssl_support_method'] = certificate.get('SSLSupportMethod')
    cert_config['min_protocol_version'] = certificate.get('MinimumProtocolVersion')
    cert_config['certificate'] = certificate.get('Certificate')
    cert_config['certificate_source'] = certificate.get('CertificateSource')

    return cert_config


def query_logging(logging_config: dict) -> dict:
    log_config = dict()
    log_config['bucket'] = logging_config.get('Bucket')
    log_config['enabled'] = logging_config.get('Enabled')
    log_config['include_cookies'] = logging_config.get('IncludeCookies')
    log_config['prefix'] = logging_config.get('Prefix')

    return log_config


def query_custom_error_responses(custom_error_responses: dict) -> list:
    custom_errors = list()
    for err_response in custom_error_responses.get('Items') or []:
        if err_response and isinstance(err_response, dict):
            response = dict()
            response['error_code'] = err_response.get('ErrorCode')
            response['response_page_path'] = err_response.get('ResponsePagePath')
            response['response_code'] = err_response.get('ResponseCode')
            response['error_caching_min_ttl'] = err_response.get('ErrorCachingMinTTL')

            custom_errors.append(response)
        else:
            if err_response is not None:
                logger.warning(f'Malformed error response. Expected a dict, got'
                               f' {type(err_response)}: {str(err_response)}')

    return custom_errors


def query_forwarded_values(forwarded_values: dict) -> dict:
    forwarded_value = dict()
    if forwarded_values and isinstance(forwarded_values, dict):
        forwarded_value['query_string'] = forwarded_values.get('QueryString')

        # cookies
        forwarded_value['cookies'] = dict()
        cookies = forwarded_values.get('Cookies')
        if cookies and isinstance(cookies, dict):
            forwarded_value['cookies']['forward'] = cookies.get('Forward')
            allowed_names = cookies.get('WhitelistedNames')
            if allowed_names and isinstance(allowed_names, dict):
                forwarded_value['cookies']['allowed_names'] = allowed_names.get('Items') or []
            else:
                if allowed_names is not None:
                    logger.warning(f'Malformed allowed names. Expected a dict, '
                                   f'got {type(allowed_names)}: '
                                   f'{str(allowed_names)}')
        else:
            if cookies is not None:
                logger.warning(f'Malformed cookies. Expected a dict, got '
                               f'{type(cookies)}: {str(cookies)}')

        # headers
        headers = forwarded_values.get('Headers')
        if headers and isinstance(headers, dict):
            forwarded_value['headers'] = headers.get('Items') or []
        else:
            if headers is not None:
                logger.warning(f'Malformed headers. Expected a dict, got '
                               f'{type(headers)}: {str(headers)}')

        # query string cache keys
        query_string_cache_keys = forwarded_values.get('QueryStringCacheKeys')
        if query_string_cache_keys and isinstance(query_string_cache_keys,
                                                  dict):
            forwarded_value['cache_keys'] = query_string_cache_keys.get('Items') or []
        else:
            if query_string_cache_keys is not None:
                logger.warning(f'Malformed query string cache keys. Expected a '
                               f'dict, got {type(query_string_cache_keys)}:'
                               f'{str(query_string_cache_keys)}')
    else:
        if forwarded_values is not None:
            logger.warning(f'Malformed forwarded values during query. Expected '
                           f'a dict, got {type(forwarded_values)}: '
                           f'{str(forwarded_values)}')

    return forwarded_value


def query_trusted_signers(trusted_signers: dict, arn: str) -> dict:
    trusted_signers_dict = dict()
    if trusted_signers and isinstance(trusted_signers, dict):
        trusted_signers_dict['signers'] = list()

        trusted_signers_dict['enabled'] = trusted_signers.get('Enabled')
        for signer in (trusted_signers.get('Items') or []):
            # extract the actual account number so not to display 'self'
            if signer == 'self':
                try:
                    result = match(ARN_PATTERN, arn)
                    signer = result.group(4)
                except Exception:
                    logger.exception(f'Unable to extract the ARN from the '
                                     f'signer: {str(signer)}')
                    continue

            trusted_signers_dict['signers'].append(signer)
    else:
        if trusted_signers is not None:
            logger.warning(f'Malformed trusted signers. Expected a dict, got '
                           f'{type(trusted_signers)}: {str(trusted_signers)}')

    return trusted_signers_dict


def query_lambda_functions(lambda_functions: dict) -> list:
    associations = list()
    if lambda_functions and isinstance(lambda_functions, dict):
        for association in lambda_functions.get('Items') or []:
            if isinstance(association, dict):
                assoc = dict()
                assoc['lambda_arn'] = association.get('LambdaFunctionARN')
                assoc['event_type'] = association.get('EventType')
                assoc['include_body'] = association.get('IncludeBody')
                associations.append(assoc)
            else:
                if association is not None:
                    logger.warning(f'Malformed lambda association. Expected a '
                                   f'dict, got {type(association)}: '
                                   f'{str(association)}')
    else:
        if lambda_functions is not None:
            logger.warning(f'Malformed lambda functions. Expected a '
                           f'dict, got {type(lambda_functions)}: '
                           f'{str(lambda_functions)}')
    return associations


def query_cache_behaviors(cache_behaviors: dict, arn: str) -> dict:
    cache_behaviors_dict = dict()

    try:  # pylint: disable=too-many-nested-blocks
        for behavior in cache_behaviors.get('Items') or []:
            if behavior and isinstance(behavior, dict):
                cache_behaviors_dict['path_pattern'] = behavior.get('PathPattern')
                cache_behaviors_dict['target_origin_id'] = behavior.get('TargetOriginId')
            else:
                if behavior is not None:
                    logger.warning(f'Malformed behavior. Expected a dict, got '
                                   f'{type(behavior)}: {str(behavior)}')

            # forwarded values
            try:
                forwarded_values = cache_behaviors.get('ForwardedValues')
                cache_behaviors_dict['forwarded_values'] = query_forwarded_values(
                    forwarded_values=forwarded_values)
            except Exception:
                logger.exception(f'Unable to query forwarded values: '
                                 f'{str(cache_behaviors.get("ForwardedValues"))}')

            # trusted signers
            try:
                trusted_signers = cache_behaviors.get('TrustedSigners')
                cache_behaviors_dict['trusted_signers'] = query_trusted_signers(
                    trusted_signers=trusted_signers,
                    arn=arn
                )
            except Exception:
                logger.exception(f'Unable to query trusted signers: '
                                 f'{str(cache_behaviors.get("TrustedSigners"))}')

            # viewer protocol policy
            cache_behaviors_dict['viewer_protocol_policy'] = cache_behaviors.get('ViewerProtocolPolicy')

            # allowed http methods
            try:
                allowed_methods = cache_behaviors.get('AllowedMethods')
                if allowed_methods and isinstance(allowed_methods, dict):
                    cache_behaviors_dict['allowed_methods'] = \
                        [method for method in (allowed_methods.get('Items') or [])]

                    # cached http methods
                    cached_methods = allowed_methods.get('CachedMethods')
                    if cached_methods and isinstance(cached_methods, dict):
                        cache_behaviors_dict['cached_methods'] = cached_methods.get('Items') or []
                    else:
                        if cached_methods is not None:
                            logger.warning(f'Malformed cache methods. Expected a '
                                           f'dict, got {type(cached_methods)}:'
                                           f'{str(cached_methods)}')
                else:
                    if allowed_methods is not None:
                        logger.warning(f'Malformed allowed methods. Expected a '
                                       f'dict, got {type(allowed_methods)}:'
                                       f'{str(allowed_methods)}')
            except Exception:
                logger.exception(f'Unable to query allowed methods: '
                                 f'{str(cache_behaviors.get("AllowedMethods"))}')

            # lambda function associations
            try:
                lambda_functions = cache_behaviors.get('LambdaFunctionAssociations')
                cache_behaviors_dict['lambda_associations'] = query_lambda_functions(
                    lambda_functions=lambda_functions)
            except Exception:
                logger.exception(f'Unable to query lambda associations: '
                                 f'{str(cache_behaviors.get("LambdaFunctionAssociations"))}')
    except Exception:
        logger.exception(f'Unable to query cache behaviors')

    return cache_behaviors_dict


def query_default_cache_behaviors(default_behaviors: dict,
                                  arn: str) -> dict:
    behaviors_dict = dict()

    behaviors_dict['target_origin_id'] = default_behaviors.get('TargetOriginId')
    behaviors_dict['min_ttl'] = default_behaviors.get('MinTTL')
    behaviors_dict['smooth_streaming'] = default_behaviors.get('SmoothStreaming')
    behaviors_dict['default_ttl'] = default_behaviors.get('DefaultTTL')
    behaviors_dict['max_ttl'] = default_behaviors.get('MaxTTL')
    behaviors_dict['compress'] = default_behaviors.get('Compress')
    behaviors_dict['field_level_encryption_id'] = default_behaviors.get('FieldLevelEncryptionId')
    behaviors_dict['price_class'] = default_behaviors.get('PriceClass')
    behaviors_dict['web_acl_id'] = default_behaviors.get('WebACLId')
    behaviors_dict['http_version'] = default_behaviors.get('HttpVersion')
    behaviors_dict['ipv6_enabled'] = default_behaviors.get('IsIPV6Enabled')
    behaviors_dict['viewer_protocol_policy'] = default_behaviors.get('ViewerProtocolPolicy')

    # forwarded values
    try:
        forwarded_values = default_behaviors.get('ForwardedValues')
        behaviors_dict['forwarded_values'] = query_forwarded_values(
            forwarded_values=forwarded_values)
    except Exception:
        logger.exception(f'Unable to query forwarded values: '
                         f'{str(default_behaviors.get("ForwardedValues"))}')

    # trusted signers
    try:
        trusted_signers = default_behaviors.get('TrustedSigners')
        behaviors_dict['trusted_signers'] = query_trusted_signers(
            trusted_signers=trusted_signers,
            arn=arn
        )
    except Exception:
        logger.exception(f'Unable to query trusted signers: '
                         f'{str(default_behaviors.get("TrustedSigners"))}')

    # allowed http methods
    try:
        allowed_methods = default_behaviors.get('AllowedMethods')
        if allowed_methods and isinstance(allowed_methods, dict):
            behaviors_dict['allowed_methods'] = allowed_methods.get('Items') or []

            # cached http methods
            cached_methods = allowed_methods.get('CachedMethods')
            if cached_methods and isinstance(cached_methods, dict):
                behaviors_dict['cached_methods'] = cached_methods.get('Items') or []
            else:
                if cached_methods is not None:
                    logger.warning(
                        f'Malformed cache methods. Expected a dict, got '
                        f'{type(cached_methods)}: {str(cached_methods)}')
        else:
            if allowed_methods is not None:
                logger.warning(
                    f'Malformed allowed methods. Expected a dict, got '
                    f'{type(allowed_methods)}: {str(allowed_methods)}')
    except Exception:
        logger.exception(f'Unable to query allowed methods:'
                         f'{str(default_behaviors.get("AllowedMethods"))}')

    # lambda function associations
    try:
        lambda_functions = default_behaviors.get('LambdaFunctionAssociations')
        behaviors_dict['lambda_associations'] = query_lambda_functions(
            lambda_functions=lambda_functions)
    except Exception:
        logger.exception(f'Unable to query lambda function associations: '
                         f'{str(default_behaviors.get("LambdaFunctionAssociations"))}')

    return behaviors_dict


def query_origin_groups(origin_groups: dict) -> list:
    origin_groups_list = list()
    # pylint: disable=too-many-nested-blocks
    for group_item in origin_groups.get('Items') or []:
        group = dict()
        if group_item and isinstance(group_item, dict):
            group['id'] = group_item.get('Id')

            try:
                failover_criteria = group_item.get('FailoverCriteria')
                if failover_criteria and isinstance(failover_criteria, dict):
                    status_codes = failover_criteria.get('StatusCodes')
                    if status_codes and isinstance(status_codes, dict):
                        group['status_codes'] = status_codes.get('Items') or []
                    else:
                        if status_codes is not None:
                            logger.warning(f'Malformed status codes. Expected a'
                                           f' dict, got {type(status_codes)}: '
                                           f'{str(status_codes)}')
                else:
                    if failover_criteria is not None:
                        logger.warning(f'Malformed failover criteria. Expected '
                                       f'a dict, got {type(failover_criteria)}:'
                                       f' {str(failover_criteria)}')
            except Exception:
                logger.exception(f'Unable to query failover criteria: '
                                 f'{str(group_item.get("FailoverCriteria"))}')

            try:
                members = group_item.get('Members')
                if members and isinstance(members, dict):
                    group['members'] = \
                        [member_item.get('OriginId') for member_item in
                         (members.get('Items') or []) if isinstance(member_item, dict)]
                else:
                    if members is not None:
                        logger.warning(f'Malformed members. Expected a dict, '
                                       f'got {type(members)}: {str(members)}')
            except Exception:
                logger.exception(f'Unable to query members: '
                                 f'{str(group_item.get("Members"))}')

            origin_groups_list.append(group)
        else:
            if group_item is not None:
                logger.warning(f'Malformed group item. Expected a dict, got '
                               f'{type(group_item)}: {str(group_item)}')

    return origin_groups_list


def query_origins(origins: dict) -> list:
    # pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements
    discovered_origins = list()

    for origin_item in origins.get('Items') or []:
        if origin_item and isinstance(origin_item, dict):
            # origin base
            origins_dict = dict()
            origins_dict['id'] = origin_item.get('Id')
            origins_dict['domain_name'] = origin_item.get('DomainName')
            origins_dict['origin_path'] = origin_item.get('OriginPath')
            origins_dict['connection_attempts'] = origin_item.get('ConnectionAttempts')
            origins_dict['connection_timeout'] = origin_item.get('ConnectionTimeout')

            # origin access id
            try:
                origin_access_id = origin_item.get('S3OriginConfig')
                if isinstance(origin_access_id, dict):
                    origins_dict['s3_origin_config'] = origin_access_id.get('OriginAccessIdentity')
                else:
                    if origin_access_id is not None:
                        logger.warning(f'Malformed origin access ID. Expected '
                                       f'a dict, got {type(origin_access_id)}:'
                                       f'{str(origin_access_id)}')
            except Exception:
                logger.exception(f'Unable to query origin access ID: '
                                 f'{str(origin_item.get("S3OriginConfig"))}')

            # custom headers
            origins_dict['custom_headers'] = dict()
            try:
                custom_headers = origin_item.get('CustomHeaders')
                if custom_headers and isinstance(custom_headers, dict):
                    custom_headers_dict = dict()
                    for header_item in custom_headers.get('Items') or []:
                        if isinstance(header_item, dict):
                            header_name = header_item.get('HeaderName')
                            header_value = header_item.get('HeaderValue')
                            if header_name and header_value:
                                custom_headers_dict[header_name] = header_value
                        else:
                            if header_item is not None:
                                logger.warning(
                                    f'Malformed header item. Expected a '
                                    f'dict, got {type(header_item)}: '
                                    f'{str(header_item)}')

                    origins_dict['custom_headers'] = custom_headers_dict
                else:
                    if custom_headers is not None:
                        logger.warning(f'Malformed custom headers. Expected a '
                                       f'dict, got {type(custom_headers)}: '
                                       f'{str(custom_headers)}')
            except Exception:
                logger.exception(f'Unable to query custom headers: '
                                 f'{str(origin_item.get("CustomHeaders"))}')

            # custom config
            origins_dict['custom_config'] = dict()
            try:
                custom_config = origin_item.get('CustomOriginConfig')
                if custom_config and isinstance(custom_config, dict):
                    custom_config_dict = dict()
                    custom_config_dict['http_port'] = custom_config.get('HTTPPort')
                    custom_config_dict['https_port'] = custom_config.get('HTTPSPort')
                    custom_config_dict['protocol_policy'] = custom_config.get('OriginProtocolPolicy')
                    custom_config_dict['read_timeout'] = custom_config.get('OriginReadTimeout')
                    custom_config_dict['keepalive_timeout'] = custom_config.get('OriginKeepaliveTimeout')
                    custom_config_dict['ssl_protocols'] = [protocol for protocol in (custom_config.get('Items') or [])]

                    origins_dict['custom_config'] = custom_config_dict
                else:
                    if custom_config is not None:
                        logger.warning(f'Malformed custom configuration. '
                                       f'Expected a dict, got '
                                       f'{type(custom_config)}: '
                                       f'{str(custom_config)}')
            except Exception:
                logger.exception(
                    f'Unable to query custom origin configuration: '
                    f'{str(origin_item.get("CustomOriginConfig"))}')

            discovered_origins.append(origins_dict)
        else:
            if origin_item is not None:
                logger.warning(f'Malformed origin item. Expected a dict, got '
                               f'{type(origin_item)}: {str(origin_item)}')

    return discovered_origins


def query_origin_names(distro: dict) -> list:
    origin_names = set()

    config = distro.get('distribution_config')
    if isinstance(config, dict):
        origins = config.get('origins')
        if origins and isinstance(origins, list):
            origins_list = [origin.get('id') for origin in origins if isinstance(origin, dict)]
            for origin in origins_list:
                if isinstance(origin, str) and '/' in origin:
                    origin_names.add(origin.split('/')[0])
                else:
                    origin_names.add(origin)
        else:
            if origins is not None:
                logger.warning(f'Malformed origins. Expected a list, got '
                               f'{type(origins)}: {str(origins)}')
    else:
        logger.warning(f'Malformed distribution configuration. Expected a dict,'
                       f' got {type(config)}: {str(config)}')

    return list(origin_names)


def populate_cloudfront_resource(client: dict) -> dict:  # pylint: disable=inconsistent-return-statements
    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks,
    cloudfront_distro = dict()

    cloudfront_client = client.get('cloudfront')
    if cloudfront_client is None:
        logger.warning(f'Unable to get a Cloudfront client')
        return {}

    logger.debug(f'Started populating Cloudfront shared resource')

    cloudfront_distro['origins'] = list()
    cloudfront_distro['distros'] = list()
    try:
        response = cloudfront_client.list_distributions()
        if not isinstance(response, dict):
            raise ValueError(f'Malformed response from list_distributions. '
                             f'Expected a dict, got {type(response)}: '
                             f'{str(response)}')

        distributions_raw = response.get('DistributionList')
        if isinstance(distributions_raw, dict):
            distributions = distributions_raw.get('Items')
            if isinstance(distributions, list):
                for distribution in distributions:
                    if isinstance(distribution, dict):
                        distro = dict()
                        distribution_id = distribution.get('Id')
                        if not isinstance(distribution_id, str):
                            raise ValueError(f'Malformed Cloudfront distribution'
                                             f' id. Expected a str, got '
                                             f'{type(distribution_id)}: '
                                             f'{str(distribution_id)}')

                        try:
                            response = cloudfront_client.get_distribution(Id=distribution_id)
                            if not isinstance(response, dict):
                                raise ValueError(
                                    f'Malformed response from get_distribution.'
                                    f' Expected a dict, got {type(response)}:'
                                    f'{str(response)}')

                            distribution_raw = response.get('Distribution')
                            if distribution_raw and isinstance(distribution_raw, dict):
                                distro['id'] = distribution_raw.get('Id')
                                distro['arn'] = distribution_raw.get('ARN')
                                distro['status'] = distribution_raw.get('Status')
                                distro['last_modified'] = distribution_raw.get('LastModifiedTime')
                                distro['in_progress_validation_batches'] = \
                                    distribution_raw.get('InProgressInvalidationBatches')
                                distro['domain_name'] = distribution_raw.get('DomainName')

                                signers = distribution_raw.get('ActiveTrustedSigners')
                                if signers and isinstance(signers, dict):
                                    distro['active_trusted_signers'] = \
                                        query_active_trusted_signers(
                                            signers=signers,
                                            arn=distribution_raw.get('ARN'))
                                else:
                                    if signers is not None:
                                        logger.warning(
                                            f'Malformed signers. Expected '
                                            f'a dict, got {type(signers)}: '
                                            f'{str(signers)}')

                                dist_config = distribution_raw.get('DistributionConfig')
                                if dist_config and isinstance(dist_config, dict):
                                    distro['distribution_config'] = \
                                        query_distribution_config(
                                            config=dist_config,
                                            arn=distribution_raw.get('ARN'))
                                else:
                                    if dist_config is not None:
                                        logger.warning(
                                            f'Malformed distribution configuration. '
                                            f'Expected a dict, got {type(dist_config)}:'
                                            f'{str(dist_config)}')

                                # stash origins for easy lookups in connections
                                processed_config = distro.get('distribution_config')
                                if processed_config and isinstance(processed_config, dict):
                                    origins = processed_config.get('domains')
                                    if isinstance(origins, list):
                                        cloudfront_distro['origins'] = origins
                                    else:
                                        if origins is not None:
                                            logger.warning(
                                                f'Malformed origins. Expected a '
                                                f'list, got {type(origins)}: '
                                                f'{str(origins)}')
                                else:
                                    if processed_config is not None:
                                        logger.warning(
                                            f'Malformed processed configuration. '
                                            f'Expected a dict, got {type(processed_config)}:'
                                            f'{str(processed_config)}')

                                cloudfront_distro['distros'].append(distro)

                                alias_ipc_recordals = distribution_raw.get('AliasICPRecordals')
                                recordals = list()
                                if alias_ipc_recordals and isinstance(alias_ipc_recordals, list):
                                    for recordal in alias_ipc_recordals:
                                        if isinstance(recordal, dict):
                                            item = dict()
                                            item['cname'] = recordal.get('CNAME')
                                            item['status'] = recordal.get('ICPRecordalStatus')
                                            recordals.append(item)
                                    cloudfront_distro['alias_ipc_recordals'] = recordals
                                else:
                                    if alias_ipc_recordals is not None:
                                        logger.warning(
                                            f'Malformed IPC recordals. Expected a '
                                            f'list, got {type(alias_ipc_recordals)}: '
                                            f'{str(alias_ipc_recordals)}')
                            else:
                                if distribution_raw is not None:
                                    logger.warning(
                                        f'Malformed distribution raw. Expected '
                                        f'a dict, got {type(distribution_raw)}: '
                                        f'{str(distribution_raw)}')
                        except Exception as e:
                            logger.exception(f'Unable to fetch Cloudfront '
                                             f'distribution configuration: {str(e)}',
                                             exc_info=True)
                    else:
                        if distribution is not None:
                            logger.warning(f'Malformed Cloudfront distribution. '
                                           f'Expected a dict, got '
                                           f'{type(distribution)}: '
                                           f'{str(distribution)}')
            else:
                if distributions is not None:
                    logger.warning(f'Malformed distributions. Expected a '
                                   f'list, got {type(distributions)}: '
                                   f'{str(distributions)}')
        else:
            if distributions_raw is not None:
                logger.warning(f'Malformed distributions raw. Expected a '
                               f'dict, got {type(distributions_raw)}: '
                               f'{str(distributions_raw)}')
    except Exception:
        logger.exception(f'Unable to connect to AWS using the cloudfront '
                         f'client of {type(cloudfront_client)}: '
                         f'{str(cloudfront_client)}')

    logger.debug(f'Finished populating Cloudfront shared resource. Found '
                 f'{len(cloudfront_distro["distros"])}')

    return cloudfront_distro


def fetch_cloudfront(device: AWSDeviceAdapter,
                     distributions: dict):
    try:  # pylint: disable=too-many-nested-blocks
        if not distributions and not isinstance(distributions, dict):
            raise ValueError(
                f'Malformed Cloudfront distributions, expected '
                f'a dict, got {type(distributions)}:'
                f'{str(distributions)}')

        origins = distributions.get('origins')
        if isinstance(origins, list):
            device_name = device.name
            if device_name and isinstance(device_name, str):
                for origin in origins:
                    if isinstance(origin, str):
                        if origin.startswith(device_name):
                            parse_cloudfront_distributions(
                                device=device,
                                distributions=distributions,
                            )
                    else:
                        if origin is not None:
                            logger.warning(f'Malformed origin. Expected a str, '
                                           f'got {type(origin)}: {str(origin)}')
            else:
                if device_name is not None:
                    logger.warning(f'Malformed device name. Expected a str, got'
                                   f' {type(device_name)}: {str(device_name)}')
        else:
            if origins is not None:
                logger.warning(f'Malformed origins. Expected a list, got '
                               f'{type(origins)}: {str(origins)}')
    except Exception:
        logger.exception(f'Unable to populate Cloudfront distributions '
                         f'for {device.aws_device_type}: {device.name}')


def parse_cloudfront_distributions(device: AWSDeviceAdapter,
                                   distributions: dict):
    origin_name = device.name

    # pylint: disable=too-many-nested-blocks
    for distribution in distributions.get('distros') or []:
        if isinstance(distribution, dict):
            distro_config = distribution.get('distribution_config')
            if isinstance(distro_config, dict):
                origins = distro_config.get('origins')
                if isinstance(origins, list):
                    for origin in origins:
                        if isinstance(origin, dict):
                            if origin_name in origin.get('domain_name'):
                                populate_device(device=device,
                                                distribution=distribution)
                        else:
                            if origin is not None:
                                logger.warning(f'Malformed distribution config '
                                               f'origin. Expected a dict, got '
                                               f'{type(origin)}: {str(origin)}')
                else:
                    if origins is not None:
                        logger.warning(f'Malformed origins. Expected a list, '
                                       f'got {type(origins)}: {str(origins)}')
            else:
                if distro_config is not None:
                    logger.warning(
                        f'Malformed distribution configuration. Expected '
                        f'a dict, got {type(distro_config)}:'
                        f'{str(distro_config)}')
        else:
            if distribution is not None:
                logger.warning(f'Malformed distribution. Expected a dict, got '
                               f'{type(distribution)}: {str(distribution)}')


def parse_behaviors(behaviors: dict) -> AWSCloudfrontCacheBehavior:  # pylint: disable=too-many-branches
    # forwarded values
    f_values = None
    forwarded_values = behaviors.get('forwarded_values')
    if forwarded_values and isinstance(forwarded_values, dict):
        cookies = forwarded_values.get('cookies')
        if cookies and isinstance(cookies, dict):
            forwarded_cookie = cookies.get('forward')
            if forwarded_cookie and forwarded_cookie not in FORWARDED_COOKIES:
                logger.error(f'New field found in forwarded values: '
                             f'{str(forwarded_cookie)} not in {FORWARDED_COOKIES}')
                forwarded_cookie = None

            cookie = AWSCloudfrontCookie(
                forward=forwarded_cookie,
                allowed_names=cookies.get('allowed_names'),
            )

            f_values = AWSCloudfrontForwardedValues(
                query_string=parse_bool(forwarded_values.get('query_string')),
                cookies=cookie,
                headers=forwarded_values.get('headers'),
                query_string_cache_keys=forwarded_values.get('query_string_cache_keys')
            )
        else:
            if cookies is not None:
                logger.warning(
                    f'Malformed cookies in behaviors config. Expected a '
                    f'dict, got {type(cookies)}: {str(cookies)}')
    else:
        if forwarded_values is not None:
            logger.warning(
                f'Malformed forwarded values during parsing. Expected a '
                f'dict, got {type(forwarded_values)}: '
                f'{str(forwarded_values)}')

    # trusted signers
    default_trusted_signer = None
    default_trusted_signers = behaviors.get('trusted_signers')
    if default_trusted_signers and isinstance(default_trusted_signers, dict):
        default_trusted_signer = AWSCloudfrontTrustedSigners(
            enabled=parse_bool(default_trusted_signers.get('enabled')),
            signers=default_trusted_signers.get('signers')
        )
    else:
        if default_trusted_signers is not None:
            logger.warning(f'Malformed default trusted signers. Expected a '
                           f'dict, got {type(default_trusted_signers)}: '
                           f'{str(default_trusted_signers)}')
    # lambda associations
    associations = list()
    lambda_associations = behaviors.get('lambda_associations')
    if isinstance(lambda_associations, list):
        for lambda_association in lambda_associations:
            if isinstance(lambda_association, dict):
                association = AWSCloudfrontLambdaAssociations(
                    arn=lambda_association.get('arn'),
                    event_type=lambda_association.get('event_type'),
                    include_body=parse_bool(lambda_association.get('include_body'))
                )
                associations.append(association)
            else:
                if lambda_association is not None:
                    logger.warning(f'Malformed lambda association. Expected a '
                                   f'dict, got {type(lambda_association)}: '
                                   f'{str(lambda_association)}')
    else:
        if lambda_associations is not None:
            logger.warning(
                f'Malformed lambda associations. Expected a list, got '
                f'{type(lambda_associations)}: {str(lambda_associations)}')

    viewer_protocol_policy = behaviors.get('viewer_protocol_policy')
    if viewer_protocol_policy and viewer_protocol_policy not in VIEWER_PROTOCOL_POLICY:
        logger.error(f'New field found in viewer protocol policy: '
                     f'{str(viewer_protocol_policy)} not in '
                     f'{str(VIEWER_PROTOCOL_POLICY)}')
        viewer_protocol_policy = None

    default_behavior = AWSCloudfrontCacheBehavior(
        target_origin_id=behaviors.get('target_origin_id'),
        forwarded_values=f_values,
        trusted_signers=default_trusted_signer,
        viewer_protocol_policy=viewer_protocol_policy,
        min_ttl=parse_int(behaviors.get('min_ttl')),
        max_ttl=parse_int(behaviors.get('max_ttl')),
        default_ttl=parse_int(behaviors.get('default_ttl')),
        allowed_methods=behaviors.get('allowed_methods'),
        cached_methods=behaviors.get('cached_methods'),
        smooth_streaming=parse_bool(behaviors.get('smooth_streaming')),
        compress=parse_bool(behaviors.get('compress')),
        lambda_function_associations=associations,
        field_level_encryption_id=behaviors.get('field_level_encryption_id'),
    )

    return default_behavior


def populate_device(device: AWSDeviceAdapter, distribution: dict):
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    logger.debug(f'Cloudfront started populating {device.aws_device_type} '
                 f'resource {device.name}')

    custom_headers = list()
    groups = list()
    cloudfront_origins = list()

    # trusted signers
    trusted_signers = distribution.get('active_trusted_signers') or {}
    trusted_signers_list = list()
    for signer in trusted_signers.get('items'):
        if isinstance(signer, dict):
            signer_details = AWSCloudfrontTrustedSignersDetails(
                account_number=signer.get('account_number'),
                keypair_ids=signer.get('keypair_ids')
            )
            trusted_signers_list.append(signer_details)
        else:
            if signer is not None:
                logger.warning(f'Malformed active trusted signer. Expected a '
                               f'dict, got {type(signer)}: '
                               f'{str(signer)}')
            continue

    active_signers = AWSCloudfrontActiveTrustedSigners(
        enabled=parse_bool(trusted_signers.get('enabled')),
        signers=trusted_signers_list
    )

    # cloudfront distribution configuration
    config = None
    distribution_config = distribution.get('distribution_config') or {}
    if isinstance(distribution_config, dict):
        origins = distribution_config.get('origins')
        for origin in origins:
            # custom headers
            if isinstance(origin, dict):
                custom_header = origin.get('custom_headers')
                if isinstance(custom_header, dict):
                    for key, value in custom_header.items():
                        new_header = AWSCustomHeaders(
                            name=key,
                            value=value,
                        )
                        custom_headers.append(new_header)
                elif isinstance(custom_header, str):
                    new_header = AWSCustomHeaders(
                        name='Name',
                        value=custom_header
                    )
                    custom_headers.append(new_header)
                else:
                    if custom_header is not None:
                        logger.warning(
                            f'Malformed custom header in distro config. '
                            f'Expected a dict, got {type(custom_header)}: '
                            f'{str(custom_header)}')

                # pylint: disable=invalid-string-quote
                # custom configuration
                custom_config = None
                custom_origin_config = origin.get('custom_config')

                if custom_origin_config and isinstance(custom_origin_config, dict):
                    protocol_policy = custom_origin_config.get('protocol_policy')
                    if protocol_policy and protocol_policy not in PROTOCOL_POLICY:
                        logger.error(f'New field found in protocol policy: '
                                     f'{str(protocol_policy)} not in'
                                     f' {str(protocol_policy)}')
                        protocol_policy = None
                    custom_config = AWSCloudfrontCustomOriginConfig(
                        http_port=parse_int(custom_origin_config.get('http_port')),
                        https_port=parse_int(custom_origin_config.get('https_port')),
                        protocol_policy=protocol_policy,
                        protocols=custom_origin_config.get('protocols'),
                        read_timeout=parse_int(custom_origin_config.get('read_timeout')),
                        keepalive_timeout=parse_int(custom_origin_config.get('keepalive_timeout')),
                    )
                else:
                    if custom_origin_config and custom_origin_config is not None:
                        logger.warning(f'Malformed custom origin config in the '
                                       f'distribution configuration. Expected a '
                                       f'dict, got {type(custom_origin_config)}: '
                                       f'{str(custom_origin_config)}')

                cloudfront_origin = AWSCloudfrontOrigins(
                    id=origin.get('id'),
                    domain_name=origin.get('domain_name'),
                    origin_path=origin.get('origin_path'),
                    s3_origin_config=origin.get('s3_origin_config'),
                    connection_attempts=parse_int(origin.get('connection_attempts')),
                    connection_timeout=parse_int(origin.get('connection_timeout')),
                    custom_headers=custom_headers,
                    custom_origin_config=custom_config,
                )
                cloudfront_origins.append(cloudfront_origin)
            else:
                if origin is not None:
                    logger.warning(f'Malformed origin in the distribution '
                                   f'configuration. Expected a dict, got '
                                   f'{type(origin)}: {str(origin)}')
                continue

        # origin groups
        origin_groups = distribution_config.get('origin_groups') or []
        for origin_group in origin_groups:
            if isinstance(origin_group, dict):
                group = AWSCloudfrontOriginGroups(
                    id=origin_group.get('id'),
                    members=origin_group.get('members'),
                    status_codes=origin_group.get('status_codes')
                )
                groups.append(group)
            else:
                if origin_group is not None:
                    logger.warning(
                        f'Malformed origin group. Expected a dict, got '
                        f'{type(origin_group)}: {str(origin_group)}')
                continue

        # default cache behaviors
        default_cache_behaviors = distribution_config.get(
            'default_cache_behaviors') or {}
        default_cache_behavior = parse_behaviors(default_cache_behaviors)

        # cache behaviors
        cache_behaviors = distribution_config.get('cache_behaviors') or {}
        cache_behavior = parse_behaviors(cache_behaviors)

        # custom error messages
        custom_error_responses = distribution_config.get('custom_error_responses') or []
        custom_responses = list()
        for error_response in custom_error_responses:
            if isinstance(error_response, dict):
                response = AWSCloudfrontCustomErrors(
                    error_code=parse_int(error_response.get('error_code')),
                    response_page_path=error_response.get('response_page_path'),
                    response_code=error_response.get('response_code'),
                    error_caching_min_ttl=parse_int(error_response.get('error_caching_min_ttl')),
                )
                custom_responses.append(response)
            else:
                if error_response is not None:
                    logger.warning(f'Malformed custom error response. Expected '
                                   f'a dict, got {type(error_response)}: '
                                   f'{str(error_response)}')
                continue

        # logging configuration
        logging_config = None
        logging_configuration = distribution_config.get('logging') or {}
        if isinstance(logging_configuration, dict):
            logging_config = AWSCloudfrontLoggingConfig(
                bucket=logging_configuration.get('bucket'),
                enabled=parse_bool(logging_configuration.get('enabled')),
                include_cookies=parse_bool(logging_configuration.get('include_cookies')),
                prefix=logging_configuration.get('prefix'),
            )
        else:
            if logging_configuration is not None:
                logger.warning(f'Malformed logging configuration. Expected a '
                               f'dict, got {type(logging_configuration)}:'
                               f'{str(logging_configuration)}')

        # viewer certificate configuration
        certificate = None
        viewer_certificate = distribution_config.get('viewer_certificate') or {}

        if isinstance(viewer_certificate, dict):
            ssl_support_method = viewer_certificate.get('ssl_support_method')
            if ssl_support_method and ssl_support_method not in SSL_SUPPORT_METHOD:
                logger.error(f'New field found in SSL support method: '
                             f'{str(ssl_support_method)} not in '
                             f'{str(ssl_support_method)}')
                ssl_support_method = None

            min_protocol_version = viewer_certificate.get('min_protocol_version')
            if min_protocol_version and min_protocol_version not in MINIMUM_PROTOCOL_VERSION:
                logger.error(f'New field found in minimum protocol version: '
                             f'{str(min_protocol_version)} not in '
                             f'{str(MINIMUM_PROTOCOL_VERSION)}')
                min_protocol_version = None

            certificate_source = viewer_certificate.get('certificate_source')
            if certificate_source and certificate_source not in CERTIFICATE_SOURCE:
                logger.error(f'New field found in certificate source:'
                             f'{str(certificate_source)} not in '
                             f'{str(CERTIFICATE_SOURCE)}')
                certificate_source = None

            certificate = AWSCloudfrontViewerCertificate(
                default_certificate=parse_bool(viewer_certificate.get('default_certificate')),
                iam_certificate_id=viewer_certificate.get('iam_certificate_id'),
                acm_certificate_arn=viewer_certificate.get('acm_certificate_arn'),
                ssl_support_method=ssl_support_method,
                min_protocol_version=min_protocol_version,
                certificate=viewer_certificate.get('certificate'),
                certificate_source=certificate_source
            )
        else:
            if viewer_certificate is not None:
                logger.warning(f'Malformed viewer certificate. Expected a dict,'
                               f' got {type(viewer_certificate)}: '
                               f'{str(viewer_certificate)}')

        # restrictions
        restriction = None
        restrictions = distribution_config.get('restriction') or {}
        if isinstance(restrictions, dict):
            restriction_type = restrictions.get('restriction_type')
            if restriction_type and restriction_type not in CLOUDFRONT_RESTRICTION_TYPE:
                logger.error(f'New field found in restriction type: '
                             f'{str(restriction_type)} not in '
                             f'{str(CLOUDFRONT_RESTRICTION_TYPE)}')
                restriction_type = None

            restriction = AWSCloudfrontRestriction(
                restriction_type=restriction_type,
                restrictions=restrictions.get('restriction')
            )
        else:
            if restrictions is not None:
                logger.warning(f'Malformed restrictions. Expected a dict, got '
                               f'{type(restrictions)}: {str(restrictions)}')

        price_class = distribution_config.get('price_class')
        if price_class and price_class not in PRICE_CLASS:
            logger.error(f'New field found in price class: {str(price_class)} '
                         f'not in {str(PRICE_CLASS)}')
            price_class = None

        http_version = distribution_config.get('http_version')
        if http_version and http_version not in HTTP_VERSION:
            logger.error(f'New field found in http version: '
                         f'{str(http_version)} not in {str(HTTP_VERSION)}')
            http_version = None

        config = AWSCloudfrontDistributionConfig(
            caller_reference=distribution_config.get('caller_reference'),
            comment=distribution_config.get('comment'),
            aliases=distribution_config.get('aliases'),
            default_root_object=distribution_config.get('default_root_object'),
            price_class=price_class,
            enabled=parse_bool(distribution_config.get('enabled')),
            web_acl_id=distribution_config.get('web_acl_id'),
            http_version=http_version,
            ipv6_enabled=parse_bool(distribution_config.get('ipv6_enabled')),
            origins=cloudfront_origins,
            origin_groups=groups,
            default_cache_behavior=default_cache_behavior,
            cache_behavior=cache_behavior,
            custom_error_responses=custom_responses,
            logging_config=logging_config,
            viewer_certificate=certificate,
            restriction=restriction,
        )
    else:
        if distribution_config is not None:
            logger.warning(f'Malformed distribution. Expected a dict, got '
                           f'{type(distribution_config)}: '
                           f'{str(distribution_config)}')

    # alias icp recordals (CN only)
    recordals = list()
    alias_icp_recordals = distribution.get('alias_ipc_recordals') or []
    if isinstance(alias_icp_recordals, list):
        for alias_icp_recordal in alias_icp_recordals:
            if isinstance(alias_icp_recordal, dict):
                recordal_status = alias_icp_recordal.get('status')
                if recordal_status and recordal_status not in ALIAS_RECORDALS_STATUS:
                    logger.error(f'New field found in alias icp recordals: '
                                 f'{str(recordal_status)} not in '
                                 f'{str(ALIAS_RECORDALS_STATUS)}')
                    recordal_status = None

                recordal = AWSCloudfrontAliasRecordals(
                    cname=alias_icp_recordal.get('cname'),
                    status=recordal_status
                )
                recordals.append(recordal)
            else:
                if alias_icp_recordal is not None:
                    logger.warning(f'Malformed Alias ICP Recordal. Expected a '
                                   f'dict, got {type(alias_icp_recordal)}: '
                                   f'{str(alias_icp_recordal)}')
                continue
    else:
        if alias_icp_recordals is not None:
            logger.warning(f'Malformed Alias ICP Recordals. Expected a list, '
                           f'got {type(alias_icp_recordals)}: '
                           f'{str(alias_icp_recordals)}')

    cloudfront = AWSCloudfrontDistribution(
        id=distribution.get('id'),
        arn=distribution.get('arn'),
        status=distribution.get('status'),
        last_modified=parse_date(distribution.get('last_modified')),
        in_progress_validation_batches=parse_int(distribution.get('in_progress_validation_batches')),
        domain_name=distribution.get('domain_name'),
        active_trusted_signers=active_signers,
        distribution_config=config,
        alias_ipc_recordals=recordals
    )

    device.cloudfront_distribution.append(cloudfront)

    logger.debug(f'Cloudfront finished populating {device.aws_device_type} '
                 f'resource {device.name}')
