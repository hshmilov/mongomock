import logging

from collections import OrderedDict
from enum import Enum

from axonius.fields import Field, ListField
from axonius.utils.parsing import normalize_var_name

logger = logging.getLogger(f'axonius.{__name__}')

"""
SmartJsonClass is a auto-json-serializable class, that allows finer declaration of possible fields and their types.
When inheriting for SmartJsonClass, use the provided Field & ListField classes to declare new fields.
                                    see fields.py for more information about creating new fields.
When setting a field, please note that a TypeError will be raise if the type is a mismatch.
"""


class SmartJsonClassMetaclass(type):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return OrderedDict()

    def __new__(cls, name, bases, namespace, **kwargs):
        # NOTE: Any change in this function requires changing the declare_new_field function as well!
        fields = []
        # Iterate all newly defined attributes, *convert* them to a proper
        # property (getter and setter) by calling Field.get_field(attr_name)
        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, Field):
                fields.append(attr_value)
                namespace[attr_name] = attr_value.get_field(attr_name)
        # Iterate other bases (support for Mixins):
        for base in bases[1:]:
            for attr_name, attr_value in base.__dict__.items():
                if isinstance(attr_value, Field):
                    fields.append(attr_value)
                    namespace[attr_name] = attr_value.get_field(attr_name)
        # append a list of the original fields to the class
        base_fields = []
        if bases:
            base_fields = getattr(bases[0], 'fields_info', [])

        # if hostname = Field(str, 'Host Name') then field.name == 'hostname' and field.title = 'Host Name'
        # The following test failure should not be possible since python does not allow it from the first place
        # but since Saiag did this before and it runs only once on a class declaration, i leave it here.
        assert len(set([field.name for field in fields])) == len(fields), \
            'Found duplicate field names, did you define two fields with the same name?'

        # Check if we have the same title in this current object. If the title is None, then it doesn't matter.
        field_titles_that_are_not_none = [field.title for field in fields if field.title]
        assert len(set(field_titles_that_are_not_none)) == len(field_titles_that_are_not_none), \
            'Found duplicate field titles, did you define two fields with the same title?'

        # Check if we defined the same name (inheritance!)
        set_intersection = set.intersection(
            set([field.name for field in fields]),
            set([field.name for field in base_fields])
        )
        assert not set_intersection, f'SmartJsonClass same-name definition! intersection: {set_intersection}'

        # Check if we defined the same title (gui inheritance!)
        set_intersection = set.intersection(
            set([field.title for field in fields if field.title]),
            set([field.title for field in base_fields if field.title])
        )
        assert not set_intersection, f'SmartJsonClass same-title definition! intersection: {set_intersection}'

        namespace['fields_info'] = fields + base_fields
        result = type.__new__(cls, name, bases, namespace)
        return result


class SmartJsonClass(metaclass=SmartJsonClassMetaclass):
    fields_info = []  # will hold the list of fields that were defined for this class
    required = []  # should contain a list of required fields, if such a list is needed

    def __init__(self, **kwargs):
        """ Creates a new SmartJsonClass and assigns the kwargs as field-values to this instance. """
        self._dict = {}  # will hold the actual values for this instance
        self._names = set()
        self.__set_raise_if_not_exist = None

        for field_names, value in kwargs.items():
            assert field_names in self.fields_info
            setattr(self, field_names, value)

        self.set_raise_if_not_exist(True)

    def __setattr__(self, name, value):
        """ Disable setting attributes not defined as Fields """
        if not name.startswith('_') and not isinstance(getattr(self.__class__, name, None), property):
            raise AttributeError(f'Unknown attribute \'{name}\' for class {self.__class__.__name__}')
        super().__setattr__(name, value)

    def __getattribute__(self, item):
        try:
            return super().__getattribute__(item)
        except KeyError:
            # If this smartjsonclass is set to not raising then we should return None on nonexisten objects
            if self.__set_raise_if_not_exist is False and \
                    not item.startswith('_') and isinstance(getattr(self.__class__, item, None), property):
                return None
            raise

    def __setitem__(self, name, value):
        self.__setattr__(name, value)

    def __getitem__(self, name):
        return super().__getattribute__(name)

    def set_raise_if_not_exist(self, should_raise: bool):
        """
        If true, if device.field is not set, will raise an exception. otherwise will return None
        :param bool should_raise: true or false.
        :return:
        """
        self.__set_raise_if_not_exist = should_raise

    def _extend_names(self, name: str, value):
        """ Extends the target_field_list (or the default field list, as implemented in _define_new_name) to contain any
            new keys that are in value. name should be the full-name of the current value.
            value can be of *any type*, supports iterating inner values of dict, list and SmartJsonClass.
        """
        if isinstance(value, dict):
            for key in value:
                self._extend_names(f'{name}.{key}', value[key])
        elif isinstance(value, list):
            for item in value:
                self._extend_names(name, item)
        elif isinstance(value, SmartJsonClass):
            for attr_name in value._names:
                sub_name = f'{name}.{attr_name}'
                if sub_name not in self._names:
                    self._define_new_name(sub_name)
                    self._names.add(sub_name)
        elif name not in self._names:
            self._define_new_name(name)
            self._names.add(name)

    def _define_new_name(self, name: str):
        """ Defines a new full-field-name """

    def does_field_exist(self, field_name):
        return field_name in [field.name for field in self.fields_info]

    def declare_new_field(self, field_name: str, field_value: Field):
        """
        Allows declaring new fields after the class has been already initialized.
        e.g.

        device.declare_new_field('screen_count', Field('Screen Count', int))
        device.screen_count = 5
        :param str field_name: the attribute name
        :param Field field_value: an instance of Field (Field/ListField)
        :return:
        """
        # NOTE: Any change in this function requires changing SmartJsonMetaClass as well!
        assert isinstance(field_value, Field), f'Field value must be instance of Field'

        # Check if we already have this key
        assert field_name not in [field.name for field in self.fields_info], \
            f'field attr-name (field_name) already exists: {field_name} '

        assert field_value.title not in [field.title for field in self.fields_info], \
            f'field gui-name (field.title) already exists: {field_value.title}'

        # This value is dynamic.
        field_value.set_dynamic(True)

        # we have to set this field as an attribute of the class itself, and without using __setattr__ which prevents
        # this. join the #ihatesaiag movement at https://ihatesaiag.com
        setattr(self.__class__, field_name, field_value.get_field(field_name))

        # add this to the fields_info variable
        self.fields_info.append(field_value)

        logger.info(f'Successfully declared dynamic field {field_name} - {str(field_value)}')

    def set_dynamic_field(self, field_name, field_value):
        field_name = normalize_var_name(field_name)
        capitalized = ' '.join([word.capitalize() for word in field_name.split(' ')])
        if not self.does_field_exist(field_name):
            self.declare_new_field(field_name, Field(str, f'{capitalized}'))
        self[field_name] = field_value

    def set_field_by_title(self, field_title: str, field_value) -> bool:
        """
        Search for a field among this type's fields, matching its title with given field_title
        If found, set the given field_value

        :param field_title: To search for
        :param field_value: To set
        :return: True if found and set, False otherwise
        """
        base = [x for x in self.fields_info if x.title and x.title.lower() == field_title.lower()]
        if not base:
            return False

        base = base[0]
        if isinstance(base, ListField):
            new_data = base.type()
            self[base.name].append(new_data)
            field = new_data
        else:
            if issubclass(base.type, SmartJsonClass):
                self[base.name] = base.type()
            field = self
        try:
            field[base.name] = field_value
        except AttributeError:
            return False
        return True

    def set_static_field(self, field_name: str, field_value) -> bool:
        """
        Made for this https://axonius.atlassian.net/wiki/spaces/AX/pages/818577415/Add+user+custom+fields+data+to+Axonius+entity+from+the+GUI
        This is needed so the GUI could specify complex paths to be set, e.g network_interfaces.mac
        network_interfaces is a list, so GUI didn't "specify" what to do with that list
        The default behavior currently implemented is that if any list is empty it will create a new item in it, and if
        it is not empty, it will edit the first one.
        :param field_name: path to change, dot separated, e.g network_interfaces.mac
        :param field_value: Value to set
        :return: True if successful, False if any place in the path doesn't exist
        """
        base = self
        field = base

        path = field_name.split('.')

        for path_current in path[:-1]:
            previous_base = base

            if isinstance(previous_base, ListField):
                base = [x for x in base._type.fields_info if x.name == path_current]
            else:
                base = [x for x in base.fields_info if x.name == path_current]

            if not base:
                return False

            base = base[0]
            if isinstance(base, ListField):
                new_data = base.type()
                if isinstance(previous_base, ListField):
                    field[path_current].append(new_data)
                else:
                    previous_base[path_current].append(new_data)
                field = new_data
            else:
                if issubclass(base.type, SmartJsonClass):
                    previous_base[path_current] = base.type()
                field = previous_base[path_current]
        try:
            field[path[-1]] = field_value
        except AttributeError:
            return False
        return True

    def to_dict(self):
        """ returns a serialized dict of this instance, can be passes as a json object """
        new_dict = dict(self._dict)
        for key in new_dict:
            if isinstance(new_dict[key], SmartJsonClass):
                new_dict[key] = new_dict[key].to_dict()
            elif isinstance(new_dict[key], list):
                new_list = []
                for item in new_dict[key]:
                    if isinstance(item, SmartJsonClass):
                        item = item.to_dict()
                    new_list.append(item)
                new_dict[key] = new_list
            elif isinstance(new_dict[key], Enum):
                new_dict[key] = new_dict[key].name
        return new_dict

    @classmethod
    def get_fields_info(cls, field_init_type=None):
        """ A class method; returns a json-scheme of the current class, containing all fields defined under it. """
        value = {"items": list(cls._get_fields_info(field_init_type)), 'type': 'array'}
        if cls.required:
            value['required'] = cls.required
        return value

    @classmethod
    def _get_fields_info(cls, field_init_type=None):
        """ helper recursive function for get_fields_info """
        for field in cls.fields_info:
            assert isinstance(field, Field)
            if field_init_type:
                if (field_init_type == 'static' and field.dynamic) or \
                        (field_init_type == 'dynamic' and not field.dynamic):
                    continue
            item = {'name': field.name}

            if issubclass(field.type, SmartJsonClass):
                field_type = list(field.type._get_fields_info(field_init_type))
                if isinstance(field, ListField):
                    field_type = {'items': field_type, 'type': 'array'}
                item['items'] = field_type
                field_type = 'array'
            else:
                field_type = field.json_name
                if isinstance(field, ListField):
                    item['items'] = {'type': field_type}
                    field_type = 'array'

            item['type'] = field_type

            if isinstance(field, ListField):
                item_dict = item['items']
            else:
                item_dict = item

            if field.title:
                item['title'] = field.title

            if field.description:
                item['description'] = field.description

            if field.format is not None:
                item_dict['format'] = field.format.name.replace('_', '-')
                item['format'] = field.format.name.replace('_', '-')

            if field.min is not None:
                item_dict['minimum'] = field.min
                item['minimum'] = field.min

            if field.max is not None:
                item_dict['maximum'] = field.max
                item['maximum'] = field.max

            if field.pattern is not None:
                item_dict['pattern'] = field.pattern
                item['pattern'] = field.pattern

            if field.enum is not None:
                enum_values = field.enum
                if isinstance(enum_values, type) and issubclass(enum_values, Enum):
                    enum_values = [value.name for value in enum_values]
                item_dict['enum'] = enum_values
                item['enum'] = enum_values

            if field.dynamic is True:
                item['dynamic'] = True
                item_dict['dynamic'] = True

            yield item
