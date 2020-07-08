import boto3

from aws_adapter.connection.structures import PROXY, REGION_NAME, AWS_CONFIG, ACCOUNT_TAG
from axonius.clients.aws.utils import get_aws_config


# pylint: disable=too-many-branches, too-many-statements
def connect_client_by_source(session: boto3.Session,
                             region_name: str,
                             client_config: dict,
                             asset_type: str = 'device'):
    params = {AWS_CONFIG: get_aws_config(client_config.get(PROXY)),
              REGION_NAME: region_name}

    clients = dict()
    errors = dict()

    if asset_type == 'users':
        clients['iam'] = session.client('iam', **params)
        clients['iam'].list_users()  # if no privileges, propagate

        try:
            c = session.client('sts', **params)
            c.get_caller_identity()
            clients['sts'] = c
        except Exception as e:
            errors['sts'] = str(e)

    else:
        try:
            c = session.client('ec2', **params)
            c.describe_instances()
            clients['ec2'] = c
        except Exception as e:
            errors['ec2'] = str(e)
            # the only service we truely need is ec2. all the rest are optional.
            # If this has failed we raise an exception
            raise ValueError(f'Could not connect: {errors.get("ec2")}')

        try:
            c = session.client('ecs', **params)
            c.list_clusters()
            clients['ecs'] = c
        except Exception as e:
            errors['ecs'] = str(e)

        try:
            c = session.client('eks', **params)
            c.list_clusters()
            clients['eks'] = c
        except Exception as e:
            if 'Could not connect to the endpoint URL' not in str(e):
                # This means EKS is not supported in this region, this is not an error.
                errors['eks'] = str(e)

        try:
            c = session.client('iam', **params)
            c.list_roles()
            clients['iam'] = c
        except Exception as e:
            errors['iam'] = str(e)

        try:
            c = session.client('elb', **params)
            c.describe_load_balancers()
            clients['elbv1'] = c
        except Exception as e:
            errors['elbv1'] = str(e)

        try:
            c = session.client('elbv2', **params)
            c.describe_load_balancers()
            clients['elbv2'] = c
        except Exception as e:
            errors['elbv2'] = str(e)

        try:
            c = session.client('ssm', **params)
            c.get_inventory_schema()
            clients['ssm'] = c
        except Exception as e:
            errors['ssm'] = str(e)

        try:
            c = session.client('rds', **params)
            c.describe_db_instances()
            clients['rds'] = c
        except Exception as e:
            errors['rds'] = str(e)

        try:
            c = session.client('s3', **params)
            c.list_buckets()
            clients['s3'] = c
        except Exception as e:
            errors['s3'] = str(e)

        if clients.get('s3'):
            # This is relevant only in the context of s3, currently
            try:
                c = session.client('cloudtrail', **params)
                c.describe_trails()
                clients['cloudtrail'] = c
            except Exception as e:
                errors['cloudtrail'] = str(e)

        try:
            c = session.client('workspaces', **params)
            c.describe_workspaces()
            clients['workspaces'] = c
        except Exception as e:
            errors['workspaces'] = str(e)

        try:
            c = session.client('sts', **params)
            c.get_caller_identity()
            clients['sts'] = c
        except Exception as e:
            errors['sts'] = str(e)

        try:
            c = session.client('lambda', **params)
            c.list_functions()
            clients['lambda'] = c
        except Exception as e:
            errors['lambda'] = str(e)

        try:
            c = session.client('route53', **params)
            c.list_hosted_zones()
            clients['route53'] = c
        except Exception as e:
            errors['route53'] = str(e)

        try:
            c = session.client('es', **params)
            c.list_domain_names()
            clients['es'] = c
        except Exception as e:
            errors['es'] = str(e)

        try:
            c = session.client('cloudfront', **params)
            c.list_distributions()
            clients['cloudfront'] = c
        except Exception as e:
            errors['cloudfront'] = str(e)

    clients['account_tag'] = client_config.get(ACCOUNT_TAG)
    clients['credentials'] = client_config
    clients['region'] = params[REGION_NAME]

    return clients, errors
