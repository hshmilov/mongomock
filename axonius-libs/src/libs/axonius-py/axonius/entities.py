"""
Axonius entities class wrappers. Implement methods to be used on devices/users from the db.
"""
import logging

from promise import Promise

from axonius.consts.gui_consts import SPECIFIC_DATA
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.utils.axonius_query_language import parse_filter, convert_db_entity_to_view_entity

logger = logging.getLogger(f'axonius.{__name__}')

import functools
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

    def get(self, internal_axon_id=None, axonius_query_language=None):
        """
        Returns a list of entities from the entity view by one of the params conditions.
        if more than one is provided, the preferred order is by the order of args.
        :param str internal_axon_id: an internal axon id.
        :param dict axonius_query_language: Axonius query language filter
        :return: a list of entities
        """
        db = self.plugin_base._entity_db_map[self.entity]
        entity_object = AXONIUS_ENTITY_BY_CLASS[self.entity]

        if internal_axon_id is not None:
            final_mongo_filter = {"internal_axon_id": internal_axon_id}
        elif axonius_query_language is not None:
            final_mongo_filter = parse_filter(axonius_query_language)
        else:
            raise ValueError("None of the query methods were provided, can't query {self.entity}")

        # Now we have the mongo filter, lets query the entities and return the entity.
        for entity_in_db in db.find(final_mongo_filter):
            yield entity_object(self.plugin_base, convert_db_entity_to_view_entity(entity_in_db))


class DevicesNamespace(EntitiesNamespace):
    """" Just a namespace for devices so that we could do self.devices.add_label """

    def __init__(self, plugin_base):
        super().__init__(plugin_base, EntityType.Devices)


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
        return self.data[SPECIFIC_DATA]

    @property
    def internal_axon_id(self):
        return self.data['internal_axon_id']

    @property
    def generic_data(self):
        return self.data['generic_data']

    def __get_all_identities(self):
        return [(plugin[PLUGIN_UNIQUE_NAME], plugin["data"]["id"])
                for plugin in self.specific_data
                if plugin.get('type') == 'entitydata']

    def flush(self):
        """
        Flushes the data from the db. We are searching by an internal axon id. So if a correlation occured,
        we will have an exception here.
        :return: None
        """
        data = self.plugin_base._entity_db_map[self.entity].find_one({"_id": ObjectId(self.data.get("_id"))})

        if data is None:
            raise ValueError("Couldn't flush from db, _id wasn't found. This might happen if the document"
                             "was deleted because of a link or unlink")

        self.data = convert_db_entity_to_view_entity(data)

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

    def add_data(self, name, data, identity_by_adapter=None, action_if_exists='replace'):
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

        return self.plugin_base.add_data_to_entity(self.entity, identity_by_adapter, name, data,
                                                   action_if_exists=action_if_exists)

    def add_adapterdata(self, data, identity_by_adapter=None, action_if_exists="replace", client_used=None):
        """
        adds an adapterdata to that device.
        :param str data: the adapterdata
        :param identity_by_adapter: an optional list of tuples of (plugin_unique_name, data.id) to tag by.
                                    if not provided, will tag by all identities.
                                    e.g. [("active_directory_adapter_123", "CN=....")]
        :param action_if_exists: "replace" to replace the tag, "update" to update the tag (in case its a dict)
        :param client_used: an optional string to indicate the client of the adapter used
        :return: the response
        """

        if identity_by_adapter is None:
            identity_by_adapter = self.__get_all_identities()

        return self.plugin_base.add_adapterdata_to_entity(self.entity, identity_by_adapter, data,
                                                          action_if_exists=action_if_exists, client_used=client_used)

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
            data = [d for d in self.specific_data if d[PLUGIN_UNIQUE_NAME] == plugin_unique_name]
            if len(data) != 1:
                raise ValueError(f"Expected to find 1 {plugin_unique_name} but found {len(data)}")

            return data[0]['data'].get(name)

    def request_action(self, name, data) -> Promise:
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

    def get_data_by_name(self, name):
        """
        Search through the list of 'data' tags for the one with requested name.

        :param name: Name of 'data' tag to search for.
        :return: The 'data' content of the found tag or None, if not found.
        """
        for generic_data_item in self.generic_data:
            if generic_data_item.get('name') and generic_data_item['name'] == name:
                return generic_data_item.get('data')
        return None


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


AXONIUS_ENTITY_BY_CLASS = {
    EntityType.Devices: AxoniusDevice,
    EntityType.Users: AxoniusUser
}
