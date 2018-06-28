"""
Axonius entities class wrappers. Implement methods to be used on devices/users from the db.
"""
import logging
logger = logging.getLogger(f"axonius.{__name__}")

import functools
import ipaddress
from enum import Enum
from bson import ObjectId


class EntityType(Enum):
    """
    Possible axonius entities
    """

    Users = "users"
    Devices = "devices"


class EntitiesNamespace(object):
    """ Just a namespace so that we could do self.devices.add_label or self.users.add_data"""

    def __init__(self, plugin_base, entity: EntityType):
        self.plugin_base = plugin_base
        self.entity = entity

        self.add_label = functools.partial(plugin_base.add_label_to_entity, entity)
        self.add_many_labels = functools.partial(plugin_base.add_many_labels_to_entity, entity)
        self.add_data = functools.partial(plugin_base.add_data_to_entity, entity)
        self.add_adapterdata = functools.partial(plugin_base.add_adapterdata_to_entity, entity)
        self.tag = functools.partial(plugin_base._tag, entity)
        self.tag_many = functools.partial(plugin_base._tag_many, entity)

    def get(self, mongo_filter=None, _id=None, internal_axon_id=None, data=None, identity_tuple=None):
        """
        Rerutns a list of entities from the entity view by one of the params conditions.
        if more than one is provided, the preferred order is by the order of args.
        :param str mongo_filter: a mongo filter, e.g. {"internal_axon_id": "123"}
        :param str _id: an id (str)
        :param str internal_axon_id: an internal axon id.
        :param dict data: a dict with elements that must be in an adapters data (real adapter or adapterdata tag)
                          e.g. {"hostname": "abcd", "name": "lalala"}
        :param tuple identity_tuple: a tuple of type (plugin_unique_name, data.id).
                                     e.g. ("ad-adapter-1234", "CN=EC2AMAZ-3B5UJ01,OU=D....")
        :return: a list of entities
        """

        db = self.plugin_base._entity_views_db_map[self.entity]
        entity_object = axonius_entity_by_entity_type[self.entity]

        if mongo_filter is not None:
            final_mongo_filter = mongo_filter
        elif _id is not None:
            final_mongo_filter = {"_id": ObjectId(_id)}
        elif internal_axon_id is not None:
            final_mongo_filter = {"internal_axon_id": internal_axon_id}
        elif data is not None:
            final_mongo_filter = {
                'specific_data': {
                    '$elemMatch': {f"data.{key}": value for key, value in data.items()}
                }
            }
        elif identity_tuple is not None:
            final_mongo_filter = {
                'specific_data': {
                    '$elemMatch': {
                        "plugin_unique_name": identity_tuple[0],
                        'data.id': identity_tuple[1]
                    }
                }
            }
        else:
            raise ValueError("None of the query methods were provided, can't query {self.entity}")

        # Now we have the mongo filter, lets query the entities and return the entity.
        for entity_in_db in db.find(final_mongo_filter):
            yield entity_object(self.plugin_base, entity_in_db)


class DevicesNamespace(EntitiesNamespace):
    """" Just a namespace for devices so that we could do self.devices.add_label """

    def __init__(self, plugin_base):
        super().__init__(plugin_base, EntityType.Devices)

    def get_all_ips(self, mongodb_filter):
        """
        Gets a list of unique ip's of all devices that answer a specific filter
        :param mongodb_filter: a filter you would normally run on self.devices_db_view.find({})
        :return: a list of ip's.
        """
        # Get a list of ip's from our devices, to request information only about them.
        db = self.plugin_base._entity_views_db_map[self.entity]

        # We extend the filter, we want it to have the ip's array.
        mongodb_filter = {"$and": [mongodb_filter, {"specific_data.data.network_interfaces.ips": {"$exists": True}}]}

        devices = db.find(
            mongodb_filter,
            projection={"_id": 0, "specific_data.data.network_interfaces.ips": 1})

        # Make a list (which is unique) of all of the ip
        ips = list()

        # Note - While we search for mongo queries that have ips, not all adapters
        # have to have them. We get devices which have at least one.

        for device in devices:
            for specific_data_record in device.get('specific_data', []):
                for network_interface in specific_data_record.get('data', {}).get('network_interfaces', []):
                    for ip in network_interface.get('ips', []):
                        # validate that this is indeed a good ipv4
                        try:
                            ip_addr = ipaddress.ip_address(ip)
                            # If we got by now (and didn't throw an exception) that's a valid ip address.
                        except Exception:
                            logger.error(f"Bypassing ip {ip}: its not a valid ip address.")
                            continue

                        # Some ip's we can have which are clearly not good.
                        if ip not in ["0.0.0.0", "255.255.255.255", "1.2.3.4", "1.1.1.1"] \
                                and ip_addr.is_loopback is False \
                                and ip_addr not in [ipaddress.ip_address("::0"), ipaddress.ip_address("::1")] \
                                and ip not in ips:
                            ips.append(ip)

        return ips


class UsersNamespace(EntitiesNamespace):
    """" Just a namespace for users so that we could do self.devices.add_label """

    def __init__(self, plugin_base):
        super().__init__(plugin_base, EntityType.Users)


class AxoniusEntity(object):
    """
    An axonius entity, like a device or a user.
    """

    def __init__(self, plugin_base, entity: EntityType, entity_in_db: dict):
        """

        :param plugin_base: a plugin_base instance.
        :param EntityType entity: "devices" or "users" as a string, to identiy what is this entity.
        :param dict entity_in_db: a dict representing the entity in the db.
        """
        self.plugin_base = plugin_base
        self.entity = entity
        self.data = entity_in_db

    @property
    def specific_data(self):
        return self.data['specific_data']

    @property
    def internal_axon_id(self):
        return self.data['internal_axon_id']

    def __get_all_identities(self):
        return [(plugin["plugin_unique_name"], plugin["data"]["id"])
                for plugin in self.data['specific_data'] if plugin.get('type') == 'entitydata']

    def flush(self):
        """
        Flushes the data from the db. We are searching by an internal axon id. So if a correlation occured,
        we will have an exception here.
        :return: None
        """
        data = self.plugin_base._entity_views_db_map[self.entity].find_one({"_id": ObjectId(self.data.get("_id"))})

        if data is None:
            raise ValueError("Couldn't flush from db, _id wasn't found. This might happen if the document"
                             "was deleted because of a link or unlink")

        self.data = data

    def add_label(self, label, is_enabled=True, identity_by_adapter=None):
        """
        adds a label to that device.
        :param str label: the label
        :param bool is_enabled: true if enabled, false otherwise.
        :param identity_by_adapter: an optional list of tuples of (plugin_unique_name, data.id) to tag by.
                                    if not provided, will tag by all identities.
                                    e.g. [("active_directory_adapter_123", "CN=....")]
        :return: the response
        """

        if identity_by_adapter is None:
            identity_by_adapter = self.__get_all_identities()

        return self.plugin_base.add_label_to_entity(self.entity, identity_by_adapter, label, is_enabled)

    def add_data(self, name, data, identity_by_adapter=None):
        """
        adds a data to that device.
        :param str name: the name of the data
        :param str data: the data of the data
        :param identity_by_adapter: an optional list of tuples of (plugin_unique_name, data.id) to tag by.
                                    if not provided, will tag by all identities.
                                    e.g. [("active_directory_adapter_123", "CN=....")]
        :return: the response
        """

        if identity_by_adapter is None:
            identity_by_adapter = self.__get_all_identities()

        return self.plugin_base.add_data_to_entity(self.entity, identity_by_adapter, name, data)

    def add_adapterdata(self, data, identity_by_adapter=None, action_if_exists="replace"):
        """
        adds an adapterdata to that device.
        :param str data: the adapterdata
        :param identity_by_adapter: an optional list of tuples of (plugin_unique_name, data.id) to tag by.
                                    if not provided, will tag by all identities.
                                    e.g. [("active_directory_adapter_123", "CN=....")]
        :param action_if_exists: "replace" to replace the tag, "update" to update the tag (in case its a dict)
        :return: the response
        """

        if identity_by_adapter is None:
            identity_by_adapter = self.__get_all_identities()

        return self.plugin_base.add_adapterdata_to_entity(self.entity, identity_by_adapter, data,
                                                          action_if_exists=action_if_exists)

    def get_first_data(self, name, plugin_unique_name=None):
        """
        returns the value of some root-level property of the data section.
        e.g, "hostname" will find the specific_data item of plugin_unique_name, and return it.
        if plugin_unique_name is empty, selects the first.

        >> get_first_data("hostname") ->
            return (self.specific_data[0].plugin_unique_name, self.specific_data[0].data.hostname)
        >> get_first_name("hostname", "ad-123") ->
            return ("ad-123-index", self.specific_data[{ad-123-index}].data.hostname)
        :param name: the name. e.g. hostname
        :param plugin_unique_name: the plugin unique name. if empty selects the first.
        :return:
        """

        assert len(self.specific_data) > 0, "specific data should always have at least 1!"
        if plugin_unique_name is None:
            for sd in self.specific_data:
                value = sd['data'].get(name)
                if value is not None:
                    return value
            return None
        else:
            data = [d for d in self.specific_data if d['plugin_unique_name'] == plugin_unique_name]
            if len(data) != 1:
                raise ValueError(f"Expected to find 1 {plugin_unique_name} but found {len(data)}")

            return data[0]['data'].get(name)

    def request_action(self, name, data):
        """
        Requests an action from the execution service.
        :param name: the name of the action, e.g. "execute_shell".
        :param data: a json representing the data.
        :return: a promise.
        """

        # Flush the device to get the latest axon id.
        self.flush()

        # return the promise.
        return self.plugin_base.request_action(name, self.internal_axon_id, data)


class AxoniusDevice(AxoniusEntity):
    """
    An axonius device, as a db representation.
    """

    def __init__(self, plugin_base, entity_in_db):
        super().__init__(plugin_base, EntityType.Devices, entity_in_db)


class AxoniusUser(AxoniusEntity):
    """
    An axonius user, as a db representation.
    """

    def __init__(self, plugin_base, entity_in_db):
        super().__init__(plugin_base, EntityType.Users, entity_in_db)


axonius_entity_by_entity_type = {
    EntityType.Devices: AxoniusDevice,
    EntityType.Users: AxoniusUser
}
