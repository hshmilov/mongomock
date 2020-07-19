import base64
import datetime
import functools
import json
import logging
import os
import socket
import subprocess
from collections import defaultdict
from typing import Optional, Callable

import kubernetes

from aws_adapter.connection.aws_cloudfront import fetch_cloudfront
from aws_adapter.connection.aws_route_table import populate_route_tables
from aws_adapter.connection.structures import AWSDeviceAdapter, AWS_POWER_STATE_MAP, AWSRole, AWSEBSVolumeAttachment, \
    AWSTagKeyValue, AWSEBSVolume
from aws_adapter.connection.utils import make_ip_rules_list, add_generic_firewall_rules, \
    describe_images_from_client_by_id, get_paginated_next_token_api, get_paginated_marker_api
from axonius.clients.shodan.connection import ShodanConnection
from axonius.devices.device_adapter import DeviceRunningState, ShodanVuln
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import parse_bool_from_raw

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-nested-blocks, too-many-branches
# pylint: disable=too-many-statements, too-many-locals, too-many-lines
def query_devices_by_client_for_all_sources(client_data: dict, options: dict):
    raw_data = dict()
    logger.info(f'Starting to query devices for region-less aws services')

    # Checks whether client_data contains IAM data
    if client_data.get('iam') is not None and options.get('fetch_instance_roles') is True:
        try:
            raw_data['instance_profiles'] = {}
            iam_client_data = client_data.get('iam')

            # For each instance that has a role attached to it, we want list all attached policies.
            # So the following code will:
            # 1. list all roles
            # 2. for each roles, list all attached policies (managed & inline)
            # 3. for each role, find all attached instance profiles for it.
            role_i = 0
            for role_answer in get_paginated_marker_api(iam_client_data.list_roles):
                for role_raw in (role_answer.get('Roles') or []):
                    # Get some basic info about this role
                    role_data = dict()
                    role_name = role_raw.get('RoleName')
                    if not role_name:
                        logger.error(f'Found a role with no role name, continuing: {role_raw}')
                        continue
                    role_i += 1
                    if role_i % 200 == 0:
                        logger.info(f'Parsing role num {role_i}: {role_name}')
                    role_data['role_name'] = role_name
                    if role_raw.get('RoleId'):
                        role_data['role_id'] = role_raw.get('RoleId')
                    if role_raw.get('Arn'):
                        role_data['arn'] = role_raw.get('Arn')
                    if role_raw.get('Description'):
                        role_data['description'] = role_raw.get('Description')

                    get_role_data = iam_client_data.get_role(RoleName=role_name)
                    permissions_boundary_dict = (get_role_data.get('Role') or {}).get('PermissionsBoundary')
                    if permissions_boundary_dict:
                        pb_type = permissions_boundary_dict.get('PermissionsBoundaryType')
                        pb_arn = permissions_boundary_dict.get('PermissionsBoundaryArn')
                        if str(pb_type).lower() == 'policy' and pb_arn:
                            # we have to get the name of this policy
                            try:
                                policy_name = iam_client_data.get_policy(PolicyArn=pb_arn)['Policy']['PolicyName']
                                role_data['permissions_boundary_policy_name'] = policy_name
                            except Exception:
                                logger.exception(f'Could not get policy for permissions boundary arn {pb_arn}, '
                                                 f'continuing')

                    # Now that we have some basic info about the role, lets get all of its attached policies.
                    attached_policies_names = []
                    for attached_policy_answer_raw in get_paginated_marker_api(
                            functools.partial(iam_client_data.list_attached_role_policies, RoleName=role_name)):
                        for attached_policy_raw in (attached_policy_answer_raw.get('AttachedPolicies') or []):
                            if attached_policy_raw.get('PolicyName'):
                                attached_policies_names.append(attached_policy_raw.get('PolicyName'))

                    for inline_policy_answer_raw in get_paginated_marker_api(
                            functools.partial(iam_client_data.list_role_policies, RoleName=role_name)):
                        attached_policies_names.extend(inline_policy_answer_raw.get('PolicyNames') or [])

                    role_data['attached_policies_names'] = attached_policies_names

                    # Now find all profile instances attached to it
                    for instance_profiles_answer_raw in get_paginated_marker_api(
                            functools.partial(iam_client_data.list_instance_profiles_for_role, RoleName=role_name)
                    ):
                        for instance_profile_raw in (instance_profiles_answer_raw.get('InstanceProfiles') or []):
                            instance_profile_id = instance_profile_raw.get('InstanceProfileId')
                            if instance_profile_id:
                                if instance_profile_id in raw_data['instance_profiles']:
                                    logger.error(f'Error! instance profile {instance_profile_id} for '
                                                 f'role {role_name} is already in raw data! continuing')
                                    continue
                                raw_data['instance_profiles'][instance_profile_id] = role_data
        except Exception:
            # We do not raise an exception here since this could be a networking exception or a programming
            # exception and we do not want the whole adapter to crash.
            logger.exception('Error while parsing iam')

    return raw_data


def query_devices_by_client_by_source(
        client_data,
        https_proxy,
        options: dict,
        cloudfront_data: dict
):
    """
    Get all AWS (EC2 & EKS) instances from a specific client

    :param str client_name: the name of the client as returned from _get_clients
    :param client_data: The data of the client, as returned from the _parse_clients_data function
        if there is EC2 data, client_data['ec2'] will contain that data
        if there is EKS data, client_data['eks'] will contain that data
    :return: http://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.describe_instances
    """
    raw_data = dict()
    region = client_data.get('region')

    if options.get('fetch_cloudfront'):
        if cloudfront_data:
            raw_data['cloudfront'] = cloudfront_data

    # Checks whether client_data contains EC2 data
    if client_data.get('ec2') is not None:
        try:
            ec2_client_data = client_data.get('ec2')
            amis = set()
            # all devices are returned at once so no progress is logged
            instances = ec2_client_data.describe_instances()
            reservations = instances['Reservations']
            while instances.get('NextToken'):
                instances = ec2_client_data.describe_instances(NextToken=instances.get('NextToken'))
                reservations += instances['Reservations']

            # get all image-ids
            for reservation in reservations:
                for instance in reservation['Instances']:
                    amis.add(instance['ImageId'])

            try:
                described_images = describe_images_from_client_by_id(ec2_client_data, amis)
            except Exception:
                described_images = {}
                logger.exception('Could not describe aws images')

            for reservation in reservations:
                for instance in reservation['Instances']:
                    instance['DescribedImage'] = described_images.get(instance['ImageId'])

            try:
                if options.get('shodan_key'):
                    shodan_connection = ShodanConnection(apikey=options.get('shodan_key'), https_proxy=https_proxy)
                    with shodan_connection:
                        for reservation in reservations:
                            for device_raw in reservation.get('Instances', []):
                                for iface in device_raw.get('NetworkInterfaces', []):
                                    assoc = iface.get('Association')
                                    if assoc is not None:
                                        public_ip = assoc.get('PublicIp')
                                        if public_ip:
                                            try:
                                                assoc['shodan_info'] = shodan_connection.get_ip_info(public_ip)
                                            except Exception as e:
                                                if '404' not in str(e):
                                                    logger.exception(f'Problem getting shodan info of {public_ip}')
            except Exception:
                logger.exception(f'Problem with Shodan')

            volumes = defaultdict(list)  # dict between instance-id and volumes
            try:
                for volumes_page in get_paginated_next_token_api(ec2_client_data.describe_volumes):
                    for volume_raw in (volumes_page.get('Volumes') or []):
                        volume_instance_id = None
                        for volume_attachment in (volume_raw.get('Attachments') or []):
                            if volume_attachment.get('InstanceId'):
                                volume_instance_id = volume_attachment.get('InstanceId')
                                # According to the docs (and UI) a volume can not be attached to multiple instances.
                                break

                        if not volume_instance_id:
                            # This is a detached ebs volume.
                            continue

                        volumes[volume_instance_id].append(volume_raw)
            except Exception:
                logger.exception(f'Problem getting volumes')

            raw_data['ec2'] = reservations
            raw_data['volumes'] = volumes
        except Exception:
            logger.exception(f'Problem parsing ec2')
            # This is a minimum
            raise

    # Checks whether client_data contains ECS data
    if client_data.get('ecs') is not None:
        try:
            raw_data['ecs'] = []
            ecs_client_data = client_data.get('ecs')

            # First, list active clusters. We set the pagination by ourselves since we have to describe these
            # clusters to see which is currently active, and list_clusters has a limit of 100.

            clusters = dict()
            for clusters_raw in get_paginated_next_token_api(
                    functools.partial(ecs_client_data.list_clusters, maxResults=100)):
                for cluster in ecs_client_data.describe_clusters(clusters=clusters_raw['clusterArns'])['clusters']:
                    try:
                        if cluster['status'].lower() == 'active':
                            clusters[cluster['clusterArn']] = cluster
                    except Exception:
                        logger.exception(f'Error parsing cluster {cluster}')

            for cluster_arn, cluster_data in clusters.items():
                # Tasks can run on Fargate or on ec2. We have to get all info about ec2 instances beforehand.
                # the maximum number describe_container_instances can query is 100, by their API.
                try:
                    container_instances = dict()
                    for containers_instances_raw in get_paginated_next_token_api(
                            functools.partial(ecs_client_data.list_container_instances, maxResults=100,
                                              cluster=cluster_arn)):
                        try:
                            containerInstanceArns = containers_instances_raw['containerInstanceArns']
                            if containerInstanceArns:
                                for container_instance in ecs_client_data.describe_container_instances(
                                        cluster=cluster_arn,
                                        containerInstances=containerInstanceArns)['containerInstances']:
                                    container_instance_arn = container_instance.get('containerInstanceArn')
                                    if container_instance_arn:
                                        container_instances[container_instance_arn] = container_instance
                        except Exception:
                            logger.exception(f'Problem in describe container instances {containers_instances_raw} ')

                    # Services has limit of 10, its the only one.
                    services = dict()
                    for services_raw in get_paginated_next_token_api(
                            functools.partial(ecs_client_data.list_services, maxResults=10, cluster=cluster_arn)
                    ):
                        try:
                            service_arns = services_raw['serviceArns']
                            if service_arns:
                                for service_raw in ecs_client_data.describe_services(
                                        cluster=cluster_arn,
                                        services=service_arns)['services']:
                                    service_name = service_raw.get('serviceName')
                                    if service_name:
                                        services[service_name] = service_raw
                        except Exception:
                            logger.exception(f'Problem describe_services for {services_raw}')

                    # Next, we list all tasks in this cluster. Like before, describe_tasks is limited to 100 so we set
                    # the pagination to this.
                    all_tasks = []
                    for tasks_arns_raw in get_paginated_next_token_api(
                            functools.partial(ecs_client_data.list_tasks, maxResults=100, cluster=cluster_arn)):
                        try:
                            task_arns = tasks_arns_raw['taskArns']
                            if task_arns:
                                all_tasks += \
                                    ecs_client_data.describe_tasks(
                                        cluster=cluster_arn, tasks=task_arns)['tasks']
                        except Exception:
                            logger.exception(f'Problem describing tasks {tasks_arns_raw}')

                    # Finally just append everything into this cluster containers
                    raw_data['ecs'].append((cluster_data, container_instances, services, all_tasks))
                except Exception:
                    logger.exception(f'Problem parsing cluster {cluster_arn} with data {cluster_data}')
        except Exception:
            raw_data['ecs'] = {}
            # We do not raise an exception here since this could be a networking exception or a programming
            # exception and we do not want the whole adapter to crash.
            logger.exception('Error while parsing ecs')

    # Checks whether client_data contains EKS data
    if client_data.get('eks') is not None:
        try:
            raw_data['eks'] = {}
            eks_client_data = client_data.get('eks')
            clusters_raw = eks_client_data.list_clusters()
            clusters = clusters_raw.get('clusters')
            while clusters_raw.get('nextToken'):
                clusters_raw = eks_client_data.list_clusters(nextToken=clusters_raw.get('nextToken'))
                clusters += clusters_raw.get('clusters')

            for cluster in clusters:
                try:
                    response = eks_client_data.describe_cluster(
                        name=cluster
                    )
                    if response.get('cluster', {}).get('status') != 'ACTIVE':
                        logger.info(f'Non active cluster {cluster}')
                        continue

                    endpoint = response['cluster']['endpoint']
                    ca_cert = response['cluster']['certificateAuthority']['data']
                    cluster_name = response['cluster']['name']

                    # We must get the token from the aws-iam-authenticator binary
                    my_env = os.environ.copy()
                    if client_data['credentials'].get('aws_access_key_id'):
                        my_env['AWS_ACCESS_KEY_ID'] = client_data['credentials']['aws_access_key_id']
                        my_env['AWS_SECRET_ACCESS_KEY'] = client_data['credentials']['aws_secret_access_key']

                    aws_iam_authenticator_process = subprocess.Popen(
                        ['aws-iam-authenticator', 'token', '-i', cluster_name],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=my_env
                    )

                    # This should be almost immediate, we put here 30 just to be sure.
                    try:
                        stdout, stderr = aws_iam_authenticator_process.communicate(timeout=30)
                    except subprocess.TimeoutExpired:
                        aws_iam_authenticator_process.kill()
                        raise ValueError(f'Maximum timeout reached for aws-iam-authenticator')

                    if aws_iam_authenticator_process.returncode != 0:
                        raise ValueError(f'error: aws-iam-authenticator return code is '
                                         f'{aws_iam_authenticator_process.returncode}, '
                                         f'stdout: {stdout}\nstderr: {stderr}')

                    api_token = json.loads(stdout.strip())

                    try:
                        api_token = api_token['status']['token']
                    except Exception:
                        raise ValueError(f'Wrong response: {api_token}')

                    # Now we have to write the ca cert to the disk to be able to pass this to kubernetes
                    ca_cert_path = os.path.join(os.path.expanduser('~'), f'{cluster_name}_ca_cert')
                    with open(ca_cert_path, 'wb') as f:
                        f.write(base64.b64decode(ca_cert))

                    try:
                        configuration = kubernetes.client.Configuration()
                        configuration.host = endpoint
                        configuration.ssl_ca_cert = ca_cert_path
                        configuration.api_key['authorization'] = 'Bearer ' + api_token

                        v1 = kubernetes.client.CoreV1Api(kubernetes.client.ApiClient(configuration))
                        ret = v1.list_pod_for_all_namespaces(watch=False)
                        raw_data['eks'][cluster_name] = (response['cluster'], ret.items)
                    finally:
                        os.remove(ca_cert_path)

                except Exception:
                    logger.exception(f'Could not get cluster info for {cluster}')
        except Exception:
            logger.exception(f'Problem parsing EKS')

    # Checks whether client_data contains ELB data
    # we declare two dicts. one that maps between instance id's and a list of load balancers that point to them
    # and one that maps between ip's and a list of load balancers that point to them.
    raw_data['elb_by_iid'] = {}
    raw_data['elb_by_ip'] = {}
    raw_data['all_elbs'] = []
    if client_data.get('elbv1') is not None and options.get('fetch_load_balancers') is True:
        try:
            elbv1_client_data = client_data.get('elbv1')
            elb_num = 0
            for elb_raw_data_answer in get_paginated_marker_api(elbv1_client_data.describe_load_balancers):
                for elb_raw in (elb_raw_data_answer.get('LoadBalancerDescriptions') or []):
                    elb_dict = {}
                    elb_name = elb_raw.get('LoadBalancerName')
                    if not elb_name:
                        logger.error(f'Error, got load balancer with no name: {elb_raw}, continuing')
                        continue
                    elb_num += 1
                    if elb_num % 200 == 0:
                        logger.info(f'Parsing elb {elb_num}: {elb_name}')

                    elb_dict['name'] = elb_name
                    elb_dict['type'] = 'classic'  # this is elbv1
                    elb_dns_name = elb_raw.get('DNSName')
                    if elb_dns_name:
                        elb_dict['dns'] = elb_dns_name
                        if options.get('parse_elb_ips'):
                            try:
                                ip = socket.gethostbyname(elb_dns_name)
                                if ip:
                                    elb_dict['last_ip_by_dns_query'] = ip
                            except Exception:
                                logger.exception(f'Could not parse ELB ip for dns {elb_dict}')
                    if elb_raw.get('Scheme'):
                        elb_dict['scheme'] = elb_raw.get('Scheme').lower()
                    if elb_raw.get('Subnets'):
                        elb_dict['subnets'] = elb_raw.get('Subnets')
                    if elb_raw.get('VPCId'):
                        elb_dict['vpcid'] = elb_raw.get('VPCId')
                    if elb_raw.get('SecurityGroups'):
                        elb_dict['security_groups'] = elb_raw.get('SecurityGroups')

                    raw_data['all_elbs'].append(elb_dict)

                    # Get the listeners, i.e. source and dest port
                    for listener_raw in (elb_raw.get('ListenerDescriptions') or []):
                        if not listener_raw.get('Listener'):
                            logger.error(f'Error parsing listener {listener_raw}, continuing')
                            continue
                        lr_data = {}
                        listener_raw_data = listener_raw['Listener']
                        if listener_raw_data.get('Protocol'):
                            lr_data['lb_protocol'] = listener_raw_data.get('Protocol')
                        if listener_raw_data.get('LoadBalancerPort'):
                            lr_data['lb_port'] = listener_raw_data.get('LoadBalancerPort')
                        if listener_raw_data.get('InstanceProtocol'):
                            lr_data['instance_protocol'] = listener_raw_data.get('InstanceProtocol')
                        if listener_raw_data.get('InstancePort'):
                            lr_data['instance_port'] = listener_raw_data.get('InstancePort')
                        # Map this lb to the instances that it points to. Note that for every listener we create
                        # this. This is the format for elbv2 so we do this like this.
                        for elb_instance_raw in elb_raw.get('Instances'):
                            iid = elb_instance_raw.get('InstanceId')
                            if not iid:
                                logger.error(f'Error pasring elb, no instance id! {elb_raw}, continuing')
                                continue
                            if iid not in raw_data['elb_by_iid']:
                                raw_data['elb_by_iid'][iid] = []
                            elb_final_dict = elb_dict.copy()
                            elb_final_dict.update(lr_data)
                            raw_data['elb_by_iid'][iid].append(elb_final_dict)
            logger.debug(f'ELBV1: Parsed {elb_num} elbs.')
        except Exception:
            # We do not raise an exception here since this could be a networking exception or a programming
            # exception and we do not want the whole adapter to crash.
            logger.exception('Error while parsing ELB v1')

    if client_data.get('elbv2') is not None and options.get('fetch_load_balancers') is True:
        try:
            elbv2_client_data = client_data.get('elbv2')
            # This one is much more complex than the elbv1 one.
            # we need to query all lb's, then all target groups
            all_elbv2_lbs_by_arn = dict()
            for elbv2_lbs_raw_answer in get_paginated_marker_api(elbv2_client_data.describe_load_balancers):
                for elbv2_raw_data in (elbv2_lbs_raw_answer.get('LoadBalancers') or []):
                    elbv2_arn = elbv2_raw_data.get('LoadBalancerArn')
                    if not elbv2_arn:
                        logger.error(f'Could not parse elb data for {elbv2_raw_data}, continuing')
                        continue
                    elbv2_data = dict()
                    if elbv2_raw_data.get('LoadBalancerName'):
                        elbv2_data['name'] = elbv2_raw_data.get('LoadBalancerName')
                    elb_dns_name = elbv2_raw_data.get('DNSName')
                    if elb_dns_name:
                        elbv2_data['dns'] = elb_dns_name
                        if options.get('parse_elb_ips'):
                            try:
                                ip = socket.gethostbyname(elb_dns_name)
                                if ip:
                                    elbv2_data['last_ip_by_dns_query'] = ip
                            except Exception:
                                logger.exception(f'Could not parse ELB ip for dns {elb_dns_name}')
                    if elbv2_raw_data.get('Scheme'):
                        elbv2_data['scheme'] = elbv2_raw_data.get('Scheme').lower()
                    if elbv2_raw_data.get('Type'):
                        elbv2_data['type'] = elbv2_raw_data.get('Type').lower()
                    if elbv2_raw_data.get('VpcId'):
                        elbv2_data['vpcid'] = elbv2_raw_data.get('VpcId')
                    if elbv2_raw_data.get('SecurityGroups'):
                        elbv2_raw_data['security_groups'] = elbv2_raw_data.get('SecurityGroups')
                    elbv2_data['subnets'] = []
                    ip_addresses = []
                    for az_raw in elbv2_raw_data.get('AvailabilityZones') or []:
                        if az_raw.get('SubnetId'):
                            elbv2_data['subnets'].append(az_raw.get('SubnetId'))
                        for lba_raw in az_raw.get('LoadBalancerAddresses') or []:
                            if lba_raw.get('IpAddress'):
                                ip_addresses.append(lba_raw.get('IpAddress'))
                    if ip_addresses:
                        elbv2_data['ips'] = ip_addresses
                    all_elbv2_lbs_by_arn[elbv2_arn] = elbv2_data
                    raw_data['all_elbs'].append(elbv2_data)

            logger.debug(f'ELBV2: Found {len(all_elbv2_lbs_by_arn)} elbs. Moving to target groups')
            tg_count = 0
            for elbv2_target_groups_answer in get_paginated_marker_api(elbv2_client_data.describe_target_groups):
                for elbv2_target_group_raw_data in (elbv2_target_groups_answer.get('TargetGroups') or []):
                    tg_arn = elbv2_target_group_raw_data.get('TargetGroupArn')
                    elbv2_tg_lb_arns = elbv2_target_group_raw_data.get('LoadBalancerArns')
                    if not elbv2_tg_lb_arns:
                        # This is a target group which is not assicaoted with any LB
                        continue

                    if not tg_arn:
                        logger.error(f'Error parsing target group, no ARN: {elbv2_target_group_raw_data}, '
                                     f'contuining.')
                        continue
                    tg_count += 1
                    if tg_count % 200 == 0:
                        logger.info(f'Parsing target group {tg_count}: {tg_arn}')
                    tg_type = elbv2_target_group_raw_data.get('TargetType')
                    if not isinstance(tg_type, str) or tg_type.lower() not in ['instance', 'ip']:
                        logger.error(f'Wrong target group type: {tg_type}, continuing')
                        continue
                    tg_type = tg_type.lower()
                    tg_dict = dict()
                    if elbv2_target_group_raw_data.get('Protocol'):
                        # These are the same in new-type lb's.
                        tg_dict['lb_protocol'] = elbv2_target_group_raw_data.get('Protocol')
                        tg_dict['instance_protocol'] = elbv2_target_group_raw_data.get('Protocol')
                    if elbv2_target_group_raw_data.get('Port'):
                        tg_dict['lb_port'] = elbv2_target_group_raw_data.get('Port')

                    elbv2_targets = dict()
                    # For each one of the target groups we must describe all targets.
                    for target_raw in (elbv2_client_data.describe_target_health(TargetGroupArn=tg_arn).get(
                            'TargetHealthDescriptions') or []):
                        target_raw_target = target_raw.get('Target')
                        if not target_raw_target:
                            logger.error(f'Error, no "target" in target health description: {target_raw}, '
                                         f'continuing')
                            continue
                        target_raw_id = target_raw_target.get('Id')
                        target_raw_port = target_raw_target.get('Port')
                        if not target_raw_id or target_raw_port is None:
                            logger.error(f'Error, target_raw is invalid: {target_raw}, continuing')
                            continue
                        final_target_dict = tg_dict.copy()
                        final_target_dict['instance_port'] = target_raw_port
                        if target_raw_id not in elbv2_targets:
                            elbv2_targets[target_raw_id] = []
                            elbv2_targets[target_raw_id].append(final_target_dict)

                    # At this point we have a dict that maps between ip/instance type targets to a partially
                    # built dict that represents an entity. we must add the lb information and then map this
                    # to the final dict of lb's by ip or target.
                    for lb_arn in elbv2_tg_lb_arns:
                        if lb_arn not in all_elbv2_lbs_by_arn:
                            logger.error(f'Error, target group refers to lb {lb_arn} that does not exist, '
                                         f'continuing')
                            continue
                        for final_target_id, final_target_obj_list in elbv2_targets.items():
                            for final_target_obj in final_target_obj_list:
                                final_lb = all_elbv2_lbs_by_arn[lb_arn].copy()
                                final_lb.update(final_target_obj)
                                if tg_type == 'ip':
                                    if final_target_id not in raw_data['elb_by_ip']:
                                        raw_data['elb_by_ip'][final_target_id] = []
                                    raw_data['elb_by_ip'][final_target_id].append(final_lb)
                                elif tg_type == 'instance':
                                    if final_target_id not in raw_data['elb_by_iid']:
                                        raw_data['elb_by_iid'][final_target_id] = []
                                    raw_data['elb_by_iid'][final_target_id].append(final_lb)
        except Exception:
            # We do not raise an exception here since this could be a networking exception or a programming
            # exception and we do not want the whole adapter to crash.
            logger.exception('Error while parsing ELB v2')

    return raw_data


def parse_raw_data_inner_regular(
        devices_raw_data,
        generic_resources: dict,
        new_device_adapter: Callable,
        options: dict
) -> Optional[AWSDeviceAdapter]:

    subnets_by_id = generic_resources.get('subnets') or {}
    vpcs_by_id = generic_resources.get('vpcs') or {}
    security_group_dict = generic_resources.get('security_groups') or {}
    route_tables = generic_resources.get('route_tables') or []

    instance_profiles_dict = devices_raw_data.get('instance_profiles') or {}
    elb_by_ip = devices_raw_data.get('elb_by_ip') or {}
    elb_by_iid = devices_raw_data.get('elb_by_iid') or {}
    all_elbs = devices_raw_data.get('all_elbs') or []
    volumes_by_iid = devices_raw_data.get('volumes') or {}
    cloudfront_distributions = devices_raw_data.get('cloudfront') or {}

    ec2_id_to_ips = dict()
    private_ips_to_ec2 = dict()

    # Checks whether devices_raw_data contains EC2 data
    if devices_raw_data.get('ec2') is not None:
        ec2_devices_raw_data = devices_raw_data.get('ec2')
        for reservation in ec2_devices_raw_data:
            for device_raw in reservation.get('Instances', []):
                device: AWSDeviceAdapter = new_device_adapter()
                device.aws_device_type = 'EC2'
                device.hostname = device_raw.get('PublicDnsName') or device_raw.get('PrivateDnsName')
                power_state = AWS_POWER_STATE_MAP.get(device_raw.get('State', {}).get('Name'),
                                                      DeviceRunningState.Unknown)
                if options.get('drop_turned_off_machines') and power_state != DeviceRunningState.TurnedOn:
                    continue
                device.power_state = power_state
                tags_dict = {i['Key']: i['Value'] for i in device_raw.get('Tags', {})}
                for key, value in tags_dict.items():
                    device.add_aws_ec2_tag(key=key, value=value)
                    device.add_key_value_tag(key, value)
                device.instance_type = device_raw['InstanceType']
                device.key_name = device_raw.get('KeyName')
                vpc_id = device_raw.get('VpcId')
                if vpc_id and isinstance(vpc_id, str):
                    vpc_id = vpc_id.lower()
                    device.vpc_id = vpc_id
                    device.vpc_name = (vpcs_by_id.get(vpc_id) or {}).get('Name')
                    try:
                        for vpc_tag_key, vpc_tag_value in (vpcs_by_id.get(vpc_id) or {}).items():
                            device.add_aws_vpc_tag(key=vpc_tag_key, value=vpc_tag_value)
                    except Exception:
                        logger.exception(f'Could not parse aws vpc tags')
                subnet_id = device_raw.get('SubnetId')
                if subnet_id:
                    device.subnet_id = subnet_id
                    device.subnet_name = (subnets_by_id.get(subnet_id) or {}).get('name')
                device.name = tags_dict.get('Name', '')
                try:
                    device.figure_os(
                        (device_raw['DescribedImage'] or {}).get(
                            'Description', '') + ' ' + device_raw.get('Platform', '')
                    )
                    try:
                        device.os.type
                    except Exception:
                        device.figure_os((device_raw['DescribedImage'] or {}).get('Name'))
                except Exception:
                    logger.exception(f'Problem parsing OS type')
                try:
                    described_image = (device_raw.get('DescribedImage') or {})
                    device.image_name = described_image.get('Name')
                    device.image_description = described_image.get('Description')
                    device.image_owner = described_image.get('OwnerId')
                    device.image_alias = described_image.get('ImageOwnerAlias')
                    device.image_is_public = parse_bool_from_raw(described_image.get('Public'))
                except Exception:
                    logger.exception(f'Could not parse image details')
                device_id = device_raw['InstanceId']
                device.id = device_id
                device.private_dns_name = device_raw.get('PrivateDnsName')
                device.public_dns_name = device_raw.get('PublicDnsName')
                try:
                    device.monitoring_state = (device_raw.get('Monitoring') or {}).get('State')
                except Exception:
                    logger.exception(f'Problem getting monitoring state for {device_raw}')
                try:
                    for security_group in (device_raw.get('SecurityGroups') or []):
                        security_group_raw = security_group_dict.get(security_group.get('GroupId'))
                        if security_group_raw and isinstance(security_group_raw, dict):
                            outbound_rules = make_ip_rules_list(
                                security_group_raw.get('IpPermissionsEgress'))
                            inbound_rules = make_ip_rules_list(security_group_raw.get('IpPermissions'))
                            device.add_aws_security_group(name=security_group.get('GroupName'),
                                                          outbound=outbound_rules,
                                                          inbound=inbound_rules)

                            try:
                                all_rules_lists = [(outbound_rules, 'EGRESS'), (inbound_rules, 'INGRESS')]
                                for rule_list, direction in all_rules_lists:
                                    add_generic_firewall_rules(
                                        device,
                                        security_group_raw.get('GroupName'),
                                        'AWS Instance Security Group',
                                        direction,
                                        rule_list
                                    )
                            except Exception:
                                logger.exception(f'Could not add generic firewall rules')
                        else:
                            device.add_aws_security_group(name=security_group.get('GroupName'))
                except Exception:
                    logger.exception(f'Problem getting security groups at {device_raw}')
                device.cloud_id = device_raw['InstanceId']
                device.cloud_provider = 'AWS'

                ec2_ips = []
                for iface in device_raw.get('NetworkInterfaces', []):
                    ec2_ips = [addr.get('PrivateIpAddress') for addr in iface.get('PrivateIpAddresses', [])]

                    assoc = iface.get('Association')
                    if assoc is not None:
                        public_ip = assoc.get('PublicIp')
                        if public_ip:
                            device.add_public_ip(public_ip)
                            ec2_ips.append(public_ip)
                            shodan_info = assoc.get('shodan_info')
                            if shodan_info:
                                shodan_info_data = shodan_info.get('data')
                                if isinstance(shodan_info_data, dict):
                                    shodan_info_data = [shodan_info_data]
                                if not isinstance(shodan_info_data, list):
                                    shodan_info_data = []
                                try:
                                    # shodan info crashed raw_data in the DB for a reason I don't know
                                    assoc.pop('shodan_info', None)
                                    vulns_dict_list = []

                                    if isinstance(shodan_info_data, list):
                                        vulns_dict_list = [shodan_info_data_item.get('vulns')
                                                           for shodan_info_data_item in shodan_info_data
                                                           if isinstance(shodan_info_data_item.get('vulns'), dict)]
                                    vulns = []
                                    for vulns_dict in vulns_dict_list:
                                        for vuln_name, vuln_data in vulns_dict.items():
                                            try:
                                                vulns.append(ShodanVuln(summary=vuln_data.get('summary'),
                                                                        vuln_name=vuln_name,
                                                                        cvss=float(vuln_data.get('cvss'))
                                                                        if vuln_data.get('cvss') is not None
                                                                        else None))
                                            except Exception:
                                                logger.exception(f'Problem adding vuln name {vuln_name}')
                                    cpe = []
                                    http_server = None
                                    http_site_map = None
                                    http_location = None
                                    http_security_text_hash = None
                                    for shoda_data_raw in shodan_info_data:
                                        try:
                                            if shoda_data_raw.get('cpe'):
                                                cpe.extend(shoda_data_raw.get('cpe'))
                                            http_info = shoda_data_raw.get('http')
                                            if http_info and isinstance(http_info, dict):
                                                if not http_server:
                                                    http_server = http_info.get('server')
                                                if not http_site_map:
                                                    http_site_map = http_info.get('sitemap')
                                                if not http_location:
                                                    http_location = http_info.get('location')
                                                if not http_security_text_hash:
                                                    http_security_text_hash = http_info.get('securitytxt_hash')
                                        except Exception:
                                            logger.exception(f'problem with shodan data raw {shoda_data_raw}')
                                        try:
                                            device.add_open_port(protocol=shoda_data_raw.get('transport'),
                                                                 port_id=shoda_data_raw.get('port'),
                                                                 service_name=(shoda_data_raw.get('_shodan')
                                                                               or {}).get('module'))
                                        except Exception:
                                            logger.exception('Failed to add open port with Shodan data')
                                    if not cpe:
                                        cpe = None
                                    device.set_shodan_data(city=shodan_info.get('city'),
                                                           region_code=shodan_info.get('region_code'),
                                                           country_name=shodan_info.get('country_name'),
                                                           org=shodan_info.get('org'),
                                                           os=shodan_info.get('os'),
                                                           cpe=cpe,
                                                           isp=shodan_info.get('isp'),
                                                           ports=shodan_info.get('ports')
                                                           if isinstance(shodan_info.get('ports'), list) else None,
                                                           vulns=vulns,
                                                           http_location=http_location,
                                                           http_server=http_server,
                                                           http_site_map=http_site_map,
                                                           http_security_text_hash=http_security_text_hash)
                                except Exception:
                                    logger.exception(f'Problem parsing shodan info for {public_ip}')

                    device.add_nic(iface.get('MacAddress'), ec2_ips)

                if ec2_ips:
                    ec2_id_to_ips[device_id] = ec2_ips

                more_ips = []

                specific_private_ip_address = device_raw.get('PrivateIpAddress')
                if specific_private_ip_address:
                    private_ips_to_ec2[specific_private_ip_address] = device_id
                    if specific_private_ip_address not in ec2_ips:
                        more_ips.append(specific_private_ip_address)

                specific_public_ip_address = device_raw.get('PublicIpAddress')
                if specific_public_ip_address and specific_public_ip_address not in ec2_ips:
                    more_ips.append(specific_public_ip_address)
                    device.add_public_ip(specific_public_ip_address)

                if more_ips:
                    device.add_ips_and_macs(ips=more_ips)
                try:
                    if AWS_POWER_STATE_MAP.get(device_raw.get('State', {}).get('Name'),
                                               DeviceRunningState.Unknown) == DeviceRunningState.TurnedOn:
                        device.last_seen = datetime.datetime.now()
                except Exception:
                    logger.exception(f'Problem adding last seen')
                try:
                    device.launch_time = parse_date(device_raw.get('LaunchTime'))
                except Exception:
                    logger.exception(f'Problem getting launch time for {device_raw}')
                device.image_id = device_raw.get('ImageId')

                try:
                    device.aws_availability_zone = (device_raw.get('Placement') or {}).get('AvailabilityZone')
                except Exception:
                    logger.exception(f'Could not parse aws availability zone')

                try:
                    iam_instance_profile_raw = device_raw.get('IamInstanceProfile')
                    if iam_instance_profile_raw:
                        iam_instance_profile_id = iam_instance_profile_raw.get('Id')
                        if iam_instance_profile_id and iam_instance_profile_id in instance_profiles_dict:
                            ec2_instance_attached_role = instance_profiles_dict[iam_instance_profile_id]
                            device.aws_attached_role = AWSRole(
                                role_name=ec2_instance_attached_role.get('role_name'),
                                role_arn=ec2_instance_attached_role.get('arn'),
                                role_id=ec2_instance_attached_role.get('role_id'),
                                role_description=ec2_instance_attached_role.get('description'),
                                role_permissions_boundary_policy_name=ec2_instance_attached_role.get(
                                    'permissions_boundary_policy_name'),
                                role_attached_policies_named=ec2_instance_attached_role.get(
                                    'attached_policies_names')
                            )
                except Exception:
                    logger.exception(f'Could not parse iam instance profile')

                try:
                    # Parse load balancers info
                    associated_lbs = []
                    for ip in ec2_ips:
                        if ip in elb_by_ip:
                            associated_lbs.extend(elb_by_ip[ip])

                    if device_id in elb_by_iid:
                        associated_lbs.extend(elb_by_iid[device_id])

                    for lb_raw in associated_lbs:
                        try:
                            ips = lb_raw.get('ips')
                            lb_scheme = lb_raw.get('scheme')
                            elb_dns = lb_raw.get('dns')
                            device.add_aws_load_balancer(
                                name=lb_raw.get('name'),
                                dns=elb_dns,
                                scheme=lb_scheme,
                                type=lb_raw.get('type'),
                                lb_protocol=lb_raw.get('lb_protocol'),
                                lb_port=lb_raw.get('lb_port'),
                                instance_protocol=lb_raw.get('instance_protocol'),
                                instance_port=lb_raw.get('instance_port'),
                                ips=ips,
                                last_ip_by_dns_query=lb_raw.get('last_ip_by_dns_query')
                            )
                            if elb_dns:
                                device.dns_names.append(elb_dns)
                        except Exception:
                            logger.exception(f'Error parsing lb: {lb_raw}')
                except Exception:
                    logger.exception(f'Error parsing load balancers information')

                try:
                    instance_volumes = volumes_by_iid.get(device_id) or []
                    device.ebs_volumes = []
                    for volume_raw in instance_volumes:
                        volume_attachments = []
                        for attachment_raw in (volume_raw.get('Attachments') or []):
                            volume_attachments.append(
                                AWSEBSVolumeAttachment(
                                    attach_time=parse_date(attachment_raw.get('AttachTime')),
                                    device=attachment_raw.get('Device'),
                                    state=attachment_raw.get('State'),
                                    delete_on_termination=attachment_raw.get('DeleteOnTermination')
                                )
                            )

                        ebs_tags_dict = {i['Key']: i['Value'] for i in (volume_raw.get('Tags') or [])}
                        ebs_tags_list = []
                        for key, value in ebs_tags_dict.items():
                            ebs_tags_list.append(AWSTagKeyValue(key=key, value=value))

                        name = ebs_tags_dict.get('Name')
                        device.ebs_volumes.append(
                            AWSEBSVolume(
                                attachments=volume_attachments,
                                name=name,
                                availability_zone=volume_raw.get('AvailabilityZone'),
                                create_time=parse_date(volume_raw.get('CreateTime')),
                                encrypted=volume_raw.get('Encrypted'),
                                kms_key_id=volume_raw.get('KmsKeyId'),
                                size=volume_raw.get('Size'),
                                snapshot_id=volume_raw.get('SnapshotId'),
                                state=volume_raw.get('State'),
                                volume_id=volume_raw.get('VolumeId'),
                                iops=volume_raw.get('Iops'),
                                tags=ebs_tags_list,
                                volume_type=volume_raw.get('VolumeType')
                            )
                        )

                        device.add_hd(
                            total_size=volume_raw.get('Size'),
                            is_encrypted=volume_raw.get('Encrypted')
                        )

                except Exception:
                    logger.exception(f'Error parsing instance volumes')

                # route tables
                if options.get('fetch_route_table_for_devices'):
                    try:
                        if not isinstance(route_tables, list):
                            raise ValueError(
                                f'Malformed route tables, expected list, '
                                f'got {type(route_tables)}')

                        populate_route_tables(device, route_tables)
                    except Exception:
                        logger.exception(f'Unable to populate route tables: '
                                         f'{str(route_tables)} for '
                                         f'{str(device.id)}')

                # cloudfront
                if options.get('fetch_cloudfront'):
                    try:
                        if cloudfront_distributions and \
                                isinstance(cloudfront_distributions, dict):
                            fetch_cloudfront(device=device,
                                             distributions=cloudfront_distributions)
                        else:
                            if cloudfront_distributions is not None:
                                logger.warning(f'Malformed Cloudfront distributions. '
                                               f'Expected a dict, got '
                                               f'{type(cloudfront_distributions)}: '
                                               f'{str(cloudfront_distributions)}')
                    except Exception:
                        logger.exception(
                            f'Unable to populate Cloudfront distributions '
                            f'for {device.aws_device_type} resource: '
                            f'{device.name}')

                device.set_raw(device_raw)
                yield device

    try:
        if devices_raw_data.get('eks') is not None:
            for cluster_name, cluster_data in devices_raw_data['eks'].items():
                eks_raw_data, kub_raw_data = cluster_data
                vpc_id = (eks_raw_data.get('resourcesVpcConfig') or {}).get('vpcId')
                if isinstance(vpc_id, str):
                    vpc_id = vpc_id.lower()

                for pod_raw in kub_raw_data:
                    try:
                        pod_raw = pod_raw.to_dict()
                        pod_spec = (pod_raw.get('spec') or {})
                        pod_status = (pod_raw.get('status') or {})
                        containers_specs = pod_spec.get('containers') or []
                        for container_index, container_raw in enumerate(
                                (pod_status.get('container_statuses') or [])):
                            try:
                                device: AWSDeviceAdapter = new_device_adapter()
                                device_id = container_raw.get('container_id')
                                if not device_id:
                                    logger.error(f'Error, container with no id: {container_raw}')
                                    continue

                                device.id = device_id

                                device.aws_device_type = 'EKS'

                                eks_host_ip = pod_status.get('host_ip')
                                eks_ec2_instance_id = private_ips_to_ec2.get(eks_host_ip)
                                device.set_instance_or_node(
                                    container_instance_name=(pod_raw.get('spec') or {}).get('node_name'),
                                    container_instance_id=eks_ec2_instance_id
                                )

                                if options.get('correlate_eks_ec2') is True:
                                    device.cloud_provider = 'AWS'
                                    device.cloud_id = eks_ec2_instance_id

                                device.vpc_id = vpc_id
                                device.vpc_name = (vpcs_by_id.get(vpc_id) or {}).get('Name')
                                try:
                                    for vpc_tag_key, vpc_tag_value in (vpcs_by_id.get(vpc_id) or {}).items():
                                        device.add_aws_vpc_tag(key=vpc_tag_key, value=vpc_tag_value)
                                except Exception:
                                    logger.exception(f'Could not parse aws vpc tags')
                                device.cluster_name = cluster_name
                                device.cluster_id = eks_raw_data.get('arn')
                                device.name = container_raw.get('name')

                                device.container_image = container_raw.get('image_id') or container_raw.get('image')

                                container_state = container_raw.get('state') or {}
                                container_state = container_state.get('running') or \
                                    container_state.get('terminated') or \
                                    container_state.get('waiting')

                                if container_state.get('running'):
                                    device.container_last_status = 'running'
                                elif container_state.get('terminated'):
                                    device.container_last_status = 'terminated'
                                elif container_state.get('waiting'):
                                    device.container_last_status = 'waiting'

                                container_spec = {}
                                if len(containers_specs) > container_index:
                                    container_spec = containers_specs[container_index]

                                container_ports = container_spec.get('ports') or []
                                for container_port_configuration in container_ports:
                                    device.add_network_binding(
                                        container_port=container_port_configuration.get('container_port'),
                                        host_port=container_port_configuration.get('host_port'),
                                        name=container_port_configuration.get('name'),
                                        protocol=container_port_configuration.get('protocol')
                                    )

                                if pod_status.get('pod_ip'):
                                    device.add_nic(ips=[pod_status.get('pod_ip')])
                                device.set_raw({
                                    'container_status': container_raw,
                                    'container_spec': container_spec,
                                    'pod': pod_raw
                                })

                                yield device
                            except Exception:
                                logger.exception(f'Error parsing container in pod: {container_raw}. bypassing')
                    except Exception:
                        logger.exception(f'Problem parsing eks pod: {pod_raw}')
    except Exception:
        logger.exception(f'Problem parsing eks data')

    try:
        # clusters contains a list of cluster dicts, each one of them
        # contains the raw data of the cluster, its services, its instances, and its tasks.
        # we start with parsing the instances, then tasks.
        clusters = devices_raw_data.get('ecs') or []
        for cluster_raw in clusters:
            cluster_data, container_instances, services, all_tasks = cluster_raw
            for task_raw in all_tasks:
                launch_type = task_raw.get('launchType')
                if not launch_type:
                    logger.error(f'Error! ECS Task with no launch type!')
                    continue
                launch_type = str(launch_type).lower()

                task_group = task_raw.get('group')
                if isinstance(task_group, str) and task_group.startswith('service:'):
                    task_service = services.get(task_group[len('service:'):])
                else:
                    task_service = None

                for container_raw in (task_raw.get('containers') or []):
                    device: AWSDeviceAdapter = new_device_adapter()
                    container_id = container_raw.get('containerArn')
                    if not container_id:
                        logger.error(f'Error, container does not have id! {container_raw}')
                        continue

                    device.id = container_id
                    device.aws_device_type = 'ECS'
                    device.name = container_raw.get('name')
                    device.cluster_id = cluster_data.get('clusterArn')
                    device.cluster_name = cluster_data.get('clusterName')
                    device.container_last_status = container_raw.get('lastStatus')

                    # Parse network interfaces
                    for network_interface in (container_raw.get('networkInterfaces') or []):
                        try:
                            ipv4_addr = network_interface.get('privateIpv4Address')
                            if isinstance(ipv4_addr, str):
                                ipv4_addr = [ipv4_addr]

                            device.add_nic(
                                name=network_interface.get('attachmentId'),
                                ips=ipv4_addr
                            )
                        except Exception:
                            logger.exception(f'Problem parsing network interface {network_interface}')

                    for network_binding in (container_raw.get('networkBindings') or []):
                        device.add_network_binding(
                            bind_ip=network_binding.get('bindIP'),
                            container_port=network_binding.get('containerPort'),
                            host_port=network_binding.get('hostPort'),
                            protocol=network_binding.get('protocol')
                        )

                    # Parse Task
                    try:
                        try:
                            connectivity_at = parse_date(task_raw.get('connectivityAt'))
                        except Exception:
                            connectivity_at = None
                            logger.exception(f'Could not parse connectivityAt of {task_raw}')
                        try:
                            created_at = parse_date(task_raw.get('createdAt'))
                        except Exception:
                            created_at = None
                            logger.exception(f'Could not parse createdAt')

                        task_arn = task_raw.get('taskArn')
                        task_definition_arn = task_raw.get('taskDefinitionArn')
                        task_name = (task_arn.split('/')[1] if len(task_arn.split('/')) > 1 else task_arn)
                        task_definition_name = task_definition_arn.split('/')[1] \
                            if len(task_definition_arn.split('/')) > 1 else task_definition_arn

                        device.set_task_or_pod(
                            connectivity_at=connectivity_at,
                            created_at=created_at,
                            connectivity=task_raw.get('connectivity'),
                            cpu_units=task_raw.get('cpu'),
                            desired_status=task_raw.get('desiredStatus'),
                            task_group=task_group,
                            task_health_status=task_raw.get('healthStatus'),
                            task_last_status=task_raw.get('lastStatus'),
                            task_launch_type=launch_type,
                            task_memory_in_mb=task_raw.get('memory'),
                            task_name=task_name,
                            task_id=task_arn,
                            task_definition_id=task_definition_arn,
                            task_definition_name=task_definition_name,
                            platform_version=task_raw.get('platformVersion')
                        )
                    except Exception:
                        logger.exception(f'Error setting task for container, task is {task_raw}')

                    # Parse Service
                    if task_service:
                        try:
                            device.set_service(
                                service_name=task_service.get('serviceName'),
                                service_id=task_service.get('serviceArn'),
                                service_status=task_service.get('status')
                            )
                        except Exception:
                            logger.exception(f'Error setting service for container, service is {task_service}')

                    # Parse specific info for ec2/fargate
                    device_vpc_id = None
                    device_subnet_id = None

                    container_instance_raw_data = {}
                    if launch_type == 'ec2':
                        device.ecs_device_type = 'EC2'
                        container_instance_arn = task_raw.get('containerInstanceArn')
                        if container_instance_arn:
                            container_instance_raw_data = container_instances.get(container_instance_arn) or {}
                            try:
                                ecs_ec2_instance_id = container_instance_raw_data.get('ec2InstanceId')
                                device.ecs_ec2_instance_id = ecs_ec2_instance_id
                                device.set_instance_or_node(
                                    container_instance_id=container_instance_arn,
                                )
                                if options.get('correlate_ecs_ec2') is True:
                                    device.cloud_provider = 'AWS'
                                    device.cloud_id = ecs_ec2_instance_id

                                for attribute in container_instance_raw_data.get('attributes'):
                                    attribute_name = attribute.get('name')
                                    attribute_value = attribute.get('value')

                                    if not isinstance(attribute_name, str) or not isinstance(attribute_value, str):
                                        continue

                                    attribute_name = attribute_name.lower()
                                    if attribute_name == 'ecs.ami-id':
                                        device.image_id = attribute_value

                                    elif attribute_name == 'ecs.vpd-id':
                                        device_vpc_id = attribute_value

                                    elif attribute_name == 'ecs.subnet-id':
                                        device_subnet_id = attribute_value

                                    elif attribute_name == 'ecs.availability-zone':
                                        device.aws_availability_zone = attribute_value

                                    elif attribute_name == 'ecs.instance-type':
                                        device.instance_type = attribute_value

                                    elif attribute_name == 'ecs.os-type':
                                        device.figure_os(attribute_value)

                                # we have no info of the ip of the container in ec2. we have to get all the ip's
                                # of this ec2 instance from the ec2 data.
                                ec2_ips = ec2_id_to_ips.get(ecs_ec2_instance_id)
                                if ec2_ips:
                                    device.add_nic(ips=ec2_ips)
                            except Exception:
                                logger.exception(f'Problem parsing specific info for ec2, container instance is '
                                                 f'{container_instance_raw_data}')
                    elif launch_type == 'fargate':
                        device.ecs_device_type = 'Fargate'
                        try:
                            attachments = task_raw.get('attachments') or []
                            attachments = [t for t in attachments if t.get('type') == 'ElasticNetworkInterface']
                            for attachment in attachments:
                                details_dict = dict()
                                for det in attachment.get('details'):
                                    try:
                                        details_dict[det['name']] = det['value']
                                    except Exception:
                                        logger.exception(f'problem parsing ecs fargate attachment {det}')

                                device_subnet_id = details_dict.get('subnetId')
                                network_interface_id = details_dict.get('networkInterfaceId')
                                mac_address = details_dict.get('macAddress')
                                private_ip = details_dict.get('privateIPv4Address')

                                if private_ip:
                                    private_ip = [private_ip]

                                device.add_nic(mac=mac_address, ips=private_ip, name=network_interface_id)

                                # There might be a connected load balancer here
                                try:
                                    if private_ip and private_ip[0] in elb_by_ip:
                                        for lb_raw in elb_by_ip[private_ip[0]]:
                                            ips = lb_raw.get('ips')
                                            lb_scheme = lb_raw.get('scheme')
                                            elb_dns = lb_raw.get('dns')
                                            device.add_aws_load_balancer(
                                                name=lb_raw.get('name'),
                                                dns=elb_dns,
                                                scheme=lb_scheme,
                                                type=lb_raw.get('type'),
                                                lb_protocol=lb_raw.get('lb_protocol'),
                                                lb_port=lb_raw.get('lb_port'),
                                                instance_protocol=lb_raw.get('instance_protocol'),
                                                instance_port=lb_raw.get('instance_port'),
                                                ips=ips,
                                                last_ip_by_dns_query=lb_raw.get('last_ip_by_dns_query')
                                            )
                                            if elb_dns:
                                                device.dns_names.append(elb_dns)
                                except Exception:
                                    logger.exception(f'Error parsing lb for Fargate')
                        except Exception:
                            logger.exception(f'Error while parsing Fargate attachments!')
                    else:
                        logger.error(f'Error! ECS Task with unrecognized launch type {launch_type}')
                        continue

                    if device_subnet_id:
                        device.subnet_id = device_subnet_id
                        subnet_info = (subnets_by_id.get(device_subnet_id) or {})
                        if subnet_info:
                            device.subnet_name = subnet_info.get('name')
                            vpc_id = subnet_info.get('vpc_id')
                            if vpc_id:
                                device_vpc_id = vpc_id
                    if device_vpc_id:
                        device.vpc_id = device_vpc_id
                        device.vpc_name = (vpcs_by_id.get(device_vpc_id) or {}).get('Name')
                        try:
                            for vpc_tag_key, vpc_tag_value in (vpcs_by_id.get(device_vpc_id) or {}).items():
                                device.add_aws_vpc_tag(key=vpc_tag_key, value=vpc_tag_value)
                        except Exception:
                            logger.exception(f'Could not parse aws vpc tags')

                    device.set_raw(
                        {
                            'task_raw': task_raw,
                            'container_raw': container_raw,
                            'service': task_service,
                            'container_instance': container_instance_raw_data
                        }
                    )
                    yield device
    except Exception:
        logger.exception(f'Problem parsing ecs data')

    # Parse ELB's
    try:
        for elb_raw in all_elbs:
            device: AWSDeviceAdapter = new_device_adapter()
            device.id = elb_raw['name']
            device.name = elb_raw['name']
            device.aws_device_type = 'ELB'
            ips = elb_raw.get('ips') or []
            last_ip_by_dns_query = elb_raw.get('last_ip_by_dns_query')
            lb_scheme = elb_raw.get('scheme')
            elb_dns = elb_raw.get('dns')
            subnets = []
            for subnet_id in (elb_raw.get('subnets') or []):
                subnet_name = (subnets_by_id.get(subnet_id) or {}).get('name')
                if subnet_name:
                    subnets.append(f'{subnet_id} ({subnet_name})')
                else:
                    subnets.append(subnet_id)
            device.add_aws_load_balancer(
                name=elb_raw.get('name'),
                dns=elb_dns,
                scheme=lb_scheme,
                type=elb_raw.get('type'),
                ips=ips,
                last_ip_by_dns_query=last_ip_by_dns_query,
                subnets=subnets
            )
            if elb_dns:
                device.dns_names.append(elb_dns)
            device.vpc_id = elb_raw.get('vpcid')
            device.vpc_name = (vpcs_by_id.get(elb_raw.get('vpcid')) or {}).get('Name')
            try:
                for vpc_tag_key, vpc_tag_value in (vpcs_by_id.get(elb_raw.get('vpcid')) or {}).items():
                    device.add_aws_vpc_tag(key=vpc_tag_key, value=vpc_tag_value)
            except Exception:
                logger.exception(f'Could not parse aws vpc tags')
            if last_ip_by_dns_query:
                ips.append(last_ip_by_dns_query)

            device.add_nic(ips=ips)

            try:
                for security_group in (elb_raw.get('security_groups') or []):
                    security_group_raw = security_group_dict.get(security_group)
                    if security_group_raw and isinstance(security_group_raw, dict):
                        outbound_rules = make_ip_rules_list(security_group_raw.get('IpPermissionsEgress'))
                        inbound_rules = make_ip_rules_list(security_group_raw.get('IpPermissions'))
                        device.add_aws_security_group(name=security_group_raw.get('GroupName'),
                                                      outbound=outbound_rules,
                                                      inbound=inbound_rules)

                        try:
                            all_rules_lists = [(outbound_rules, 'EGRESS'), (inbound_rules, 'INGRESS')]
                            for rule_list, direction in all_rules_lists:
                                add_generic_firewall_rules(
                                    device,
                                    security_group_raw.get('GroupName'),
                                    'AWS ELB Security Group',
                                    direction,
                                    rule_list
                                )
                        except Exception:
                            logger.exception(f'Could not add generic firewall rules')
                    else:
                        if security_group_raw:
                            device.add_aws_security_group(name=security_group_raw.get('GroupName'))
            except Exception:
                logger.exception(f'Problem getting security groups for elb')

            # route tables
            if options.get('fetch_route_table_for_devices'):
                try:
                    if not isinstance(route_tables, list):
                        raise ValueError(f'Malformed route tables, expected '
                                         f'list, got {type(route_tables)}')

                    populate_route_tables(device, route_tables)
                except Exception:
                    logger.exception(f'Unable to populate route tables: '
                                     f'{str(route_tables)} for '
                                     f'{str(device.id)}')

            # cloudfront
            if options.get('fetch_cloudfront'):
                try:
                    if cloudfront_distributions and \
                            isinstance(cloudfront_distributions, dict):
                        fetch_cloudfront(device=device,
                                         distributions=cloudfront_distributions)
                    else:
                        if cloudfront_distributions is not None:
                            logger.warning(
                                f'Malformed Cloudfront distributions. '
                                f'Expected a dict, got '
                                f'{type(cloudfront_distributions)}: '
                                f'{str(cloudfront_distributions)}')
                except Exception:
                    logger.exception(
                        f'Unable to populate Cloudfront distributions '
                        f'for {device.aws_device_type} resource: '
                        f'{device.name}')

            device.set_raw(elb_raw)
            yield device
    except Exception:
        logger.exception(f'Failure adding ELBs')
