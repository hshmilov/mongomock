import logging
from collections import defaultdict
from typing import Union, Optional, Dict

# pylint: disable=import-error
import oci
import oci.util
from oci.config import validate_config
from oci.retry import DEFAULT_RETRY_STRATEGY

from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.oracle_cloud.consts import YieldMode, ORACLE_KEY_FILE, ORACLE_TENANCY, MAX_NUMBER_OF_DEVICES

logger = logging.getLogger(f'axonius.{__name__}')


class OracleCloudConnection:
    def __init__(self,
                 client_config: dict,
                 key_content: bytes,
                 ):
        self._client_config = client_config.copy()
        self.__key_file = self._client_config.pop(ORACLE_KEY_FILE, None)
        self._client_config['key_content'] = key_content
        self._compute: Optional[oci.core.ComputeClient] = None
        self._network: Optional[oci.core.VirtualNetworkClient] = None
        self._identity: Optional[oci.identity.IdentityClient] = None
        self._tenant: str = client_config.get(ORACLE_TENANCY) or 'unknown-tenancy'
        self._tenant_compartment: Optional[oci.identity.models.Compartment] = None

    def _connect(self):
        try:
            validate_config(self._client_config)
        except Exception as e:
            message = f'Invalid configuration. Errors: {str(e)}'
            logger.exception(message)
            raise ClientConnectionException(message)
        if not self._compute:
            self._compute = oci.core.ComputeClient(self._client_config, retry_strategy=DEFAULT_RETRY_STRATEGY)
        if not self._network:
            self._network = oci.core.VirtualNetworkClient(self._client_config, retry_strategy=DEFAULT_RETRY_STRATEGY)
        if not self._identity:
            self._identity = oci.identity.IdentityClient(self._client_config, retry_strategy=DEFAULT_RETRY_STRATEGY)

    def connect(self):
        try:
            # verify config and connect
            self._connect()
            # set tenant compartment obj, which also tests for permissions
            self._tenant_compartment = self._identity.get_compartment(self._tenant).data
        except Exception as e:
            raise ClientConnectionException(f'Error: Failed to connect OCI client. '
                                            f'Please check config and permissions: {str(e)}')

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def iter_compartments(self):
        """
        Iterate over all the compartments under the tenancy, including root
        :return: List of compartments
        :rtype: :class:`identity.models.Compartment`
        """
        if not self._tenant_compartment:
            self.connect()
        yield self._tenant_compartment
        compartments = self._paged_get(
            self._identity.list_compartments,
            yield_mode=YieldMode.MODEL,
            compartment_id=self._tenant_compartment.id,
            compartment_id_in_subtree=True
        )
        yield from compartments

    def list_compartments(self):
        """Get a list of all compartments in the tenant, including root"""
        return list(self.iter_compartments())

    def _iter_devices_in_compartment(self, compartment):
        all_instances = self._paged_get(
            self._compute.list_instances,
            yield_mode=YieldMode.MODEL,
            compartment_id=compartment.id
        )
        yield from all_instances

    def _iter_users_in_tenant(self, tenancy_id: str = None):
        all_users = self._paged_get(
            self._identity.list_users,
            yield_mode=YieldMode.MODEL,
            compartment_id=tenancy_id or self._tenant_compartment.id
        )
        yield from all_users

    def _list_vnics_for_instance(self, instance: oci.core.models.Instance):
        vnic_attachments = self._paged_get(
            self._compute.list_vnic_attachments,
            yield_mode=YieldMode.MODEL,
            compartment_id=instance.compartment_id,
            instance_id=instance.id
        )
        for vnic_attach in vnic_attachments:
            yield self._network.get_vnic(vnic_attach.vnic_id).data

    def _list_groups_in_tenant(self, tenancy_id: str = None):
        all_groups = self._paged_get(
            self._identity.list_groups,
            yield_mode=YieldMode.MODEL,
            compartment_id=tenancy_id or self._tenant_compartment.id
        )
        yield from all_groups

    def _get_groups_by_groupid(self) -> dict:
        groups_by_id = dict()
        for group in self._list_groups_in_tenant():
            groups_by_id[group.id] = group
        return groups_by_id

    def _iter_user_apikeys(self, user_obj: oci.identity.models.User):
        for key in self._identity.list_api_keys(user_obj.id).data:
            key.key_value = ''  # Clear the key value
            yield key

    def _list_ugms_for_user(self, user_id):
        yield from self._paged_get(
            self._identity.list_user_group_memberships,
            yield_mode=YieldMode.MODEL,
            compartment_id=self._tenant_compartment.id,
            user_id=user_id
        )

    def get_users_list(self, serialize_to_dict=False):
        groups_by_id: Dict[str, oci.identity.models.Group] = self._get_groups_by_groupid()

        count_users = 0
        # users are all always in the root compartment!
        for user_obj in self._iter_users_in_tenant():
            if count_users >= MAX_NUMBER_OF_DEVICES:
                logger.info(f'Reached max number of users: {count_users}.')
                break
            memberships = self._list_ugms_for_user(user_obj.id)
            # add api keys
            user_obj.x_api_keys = list(self._iter_user_apikeys(user_obj))
            # add groups
            user_obj.x_groups = list()
            for ugn in memberships or []:
                group = groups_by_id.get(ugn.group_id)
                if group:
                    user_obj.x_groups.append(group)
            # Now serialize or return as-is
            if serialize_to_dict:
                yield self.serialize_user(user_obj)
            else:
                yield user_obj
            count_users += 1
        logger.info(f'Finished yielding users, got {count_users}')

    @staticmethod
    def serialize_user(user_obj: oci.identity.models.User):
        user_dict = oci.util.to_dict(user_obj)
        if hasattr(user_obj, 'x_api_keys'):
            user_dict['x_api_keys'] = oci.util.to_dict(user_obj.x_api_keys)
        if hasattr(user_obj, 'x_groups'):
            user_dict['x_groups'] = oci.util.to_dict(user_obj.x_groups)
        return user_dict

    @staticmethod
    def _get_nsg_ids_for_vnic_list(vnic_list):
        all_nsgs = list()
        for vnic in vnic_list:
            if vnic.nsg_ids and isinstance(vnic.nsg_ids, list):
                all_nsgs.extend(vnic.nsg_ids)
        return list(set(all_nsgs))  # remove duplicates

    def get_nsg_rules(self, nsg_ids: Union[list, str]):
        if isinstance(nsg_ids, str):
            nsg_ids = [nsg_ids]
        for nsg_id in nsg_ids:
            yield {
                nsg_id: self._get_all(
                    self._network.list_network_security_group_security_rules,
                    yield_mode=YieldMode.MODEL,
                    network_security_group_id=nsg_id
                )
            }

    def flatten_device(self,
                       device_obj,
                       network_info,
                       nsg_rules,
                       vcn_ids,
                       vcn_infos,
                       serialize=False):
        """
        Flatten a device's information to a dict:
        {
            'general_info': device basic information (id, name, etc),
            'network_info': list of vnics (ips and mac addresses, etc.),
            'network_security_rules': list of network-security-group rules (inbound/outbound, ports, etc.),
            'tenancy': Tenancy (root) compartment ID,
            'vcn_ids': List of virtual cloud network ids (strings),
            'vcn_infos': List of vcn info objects
        }
        If Serialize is set to True, then the items in the dictionary will be serialized to dicts.
        Keep Serialize as False to keep the items as Model objects (as in OCI model)
        :param device_obj: device (instance) object
        :param network_info: list of VNIC objects
        :param nsg_rules: list of network-security-group-security-rule objects
        :param vcn_ids: list of vcn ids
        :param vcn_infos: list of vcn info objects
        :param serialize: Whether or not to serialize the objects into dictionaries. Default: False
        :type serialize: bool
        :return: A dictionary representing a single device (Oracle Cloud instance)
        """
        device_raw_dict = {
            'general_info': device_obj,
            'network_info': network_info,
            'network_security_rules': nsg_rules,
            'tenancy': self._tenant,
            'vcn_ids': vcn_ids,
            'vcn_infos': vcn_infos
        }
        if serialize:
            return self.serialize_device_dict(device_raw_dict)
        return device_raw_dict

    @staticmethod
    def serialize_device_dict(device_raw_dict, cleanup: bool = True):
        if cleanup:
            device_raw_dict.pop('vcn_infos', None)  # Pop unnecessarily spammy stuff
            device_raw_dict.pop('nsg_rules', None)
        result = {}
        for key, value in device_raw_dict.items():
            result[key] = oci.util.to_dict(value)
        return result

    def get_devices(self, serialize_to_dict=False):
        """
        Get a list of all devices.
        A device is represented as a dictionary of OCI model objects.
        If Serialize_to_dict is set, then the OCI model objects are also converted to dictionaries.
        :param serialize_to_dict: Convert OCI model objects to dicts (default False)
        :return: A list of devices, with network info and nsg rules added.
        """
        count_devices = 0
        all_vcns = self.get_vcn_infos()
        for compartment in self.iter_compartments():
            logger.info(f'Getting devices from compartment {compartment.name}')
            for device_obj in self._iter_devices_in_compartment(compartment):
                if count_devices >= MAX_NUMBER_OF_DEVICES:
                    logger.info(f'Reached max number of devices: {count_devices}.')
                    break
                try:
                    vnics = list(self._list_vnics_for_instance(device_obj))
                    vcn_ids = list(self._get_vnic_vcn(vnic) for vnic in vnics)
                    vcn_infos = list(all_vcns.get(vcn) for vcn in vcn_ids if vcn in all_vcns)
                    nsg_ids = self._get_nsg_ids_for_vnic_list(vnics)
                    nsg_rules = self.get_nsg_rules(nsg_ids)
                except Exception:
                    logger.exception(f'Failed to get network information for device {device_obj}')
                    vnics = list()
                    vcn_ids = list()
                    vcn_infos = list()
                    nsg_rules = list()
                yield self.flatten_device(device_obj, vnics, nsg_rules, vcn_ids, vcn_infos, serialize_to_dict)
                count_devices += 1
        logger.info(f'Finished yielding devices, got {count_devices}')

    @staticmethod
    def _get_all(method,
                 *args,
                 yield_mode: Union[str, YieldMode, None] = YieldMode.DEFAULT,
                 **kwargs):
        """
        Like paged_get but not paged
        """
        return list(OracleCloudConnection._paged_get(method, *args, yield_mode=yield_mode, **kwargs))

    @staticmethod
    def _paged_get(method, *args,
                   yield_mode: Union[YieldMode, str, None] = YieldMode.DEFAULT,
                   **kwargs):
        """
        Perform the ```method``` request using oci pagination utility
        :param method: A reference to the list operation which we will call
        :param args: Positional arguments for the method
        :param yield_mode: either 'response' or 'record'. use 'response' to get raw response, or 'record' to parse
        the response.data() into an iterator of the relevant model objects. Default: 'response'
        see for reference:
        https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/api/pagination.html
        :type yield_mode: str or use the YieldMode enum for convenience
        :param kwargs: Keyword arguments for the mnethod
        :return: A generator that, depending on the yield_mode,
            will yield either `Response` objects or the individual model
            objects which are contained within the response’s `data` attribute
            (which should be a list of model objects)
        """
        yield from oci.pagination.list_call_get_all_results_generator(
            method, str(yield_mode), *args, **kwargs
        )

    def get_security_lists_in_vcn(self, vcn_obj: oci.core.models.Vcn):
        return list(self._paged_get(
            self._network.list_security_lists,
            yield_mode=YieldMode.MODEL,
            compartment_id=vcn_obj.compartment_id,
            vcn_id=vcn_obj.id
        ))

    def list_vcns_in_compartment(self, compartment_id=None):
        yield from self._paged_get(
            self._network.list_vcns,
            yield_mode=YieldMode.MODEL,
            compartment_id=compartment_id or self._tenant
        )

    def list_all_vcns(self):
        for compartment in self.iter_compartments():
            yield from self.list_vcns_in_compartment(compartment.id)

    def _get_vnic_vcn(self, vnic: oci.core.models.Vnic):
        """
        VCN has subnets. Subnets have VNICs.
        """
        if not vnic.subnet_id:
            return None
        return self._network.get_subnet(vnic.subnet_id).data.vcn_id

    def get_vcn_infos(self):
        vcn_info = defaultdict(dict)
        for compartment in self.iter_compartments():
            for vcn in self.list_vcns_in_compartment(compartment.id):
                vcn: oci.core.models.Vcn
                sec_lists = self.get_security_lists_in_vcn(vcn)
                default_sec_list = self._network.get_security_list(vcn.default_security_list_id).data
                try:
                    sec_lists.remove(default_sec_list)
                except Exception:
                    logger.debug(f'Failed to remove sec list {default_sec_list} from sec lists', exc_info=True)
                vcn_info[vcn.id]['sec_lists'] = sec_lists
                vcn_info[vcn.id]['default_sec_list'] = default_sec_list
        return vcn_info

    def cis_get_log_retention_days(self) -> int:
        audit_client = oci.audit.AuditClient(self._client_config, retry_strategy=DEFAULT_RETRY_STRATEGY)
        audit_config = audit_client.get_configuration(self._tenant).data
        audit_config: oci.audit.models.Configuration
        return audit_config.retention_period_days

    def get_query_data(self, query_text):
        search_client = oci.resource_search.ResourceSearchClient(self._client_config,
                                                                 retry_strategy=DEFAULT_RETRY_STRATEGY)
        structured_search = oci.resource_search.models.StructuredSearchDetails(
            query=query_text,
            type='Structured',
            matching_context_type=oci.resource_search.models.SearchDetails.MATCHING_CONTEXT_TYPE_NONE
        )
        return search_client.search_resources(structured_search)
