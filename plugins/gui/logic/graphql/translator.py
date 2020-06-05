# pylint: disable=invalid-string-quote, invalid-triple-quote
import typing
import datetime
from cachetools import LFUCache, cached

import axonius.pql as _pql
from axonius.entities import EntityType
from axonius.utils.axonius_query_language import process_filter
from gui.logic.graphql.builder import GqlQuery

AQL_LOGICAL_AND = '$and'
AQL_LOGICAL_OR = '$or'

# Convert AQL logical terms to GraphQL (SqlGen) logical terms.
LOGICAL_TERM_CONVERTER = {
    '$and': 'AND',
    '$or': 'OR',
    '$not': 'NOT',
}

# Mapping of all methods based on the operator
VALUE_COMPARISON_METHODS = {
    '$regex': lambda x: {'ilike': f'%{x.lstrip("^").rstrip("$")}%'},
    '$not_regex': lambda x: {'not_ilike': f'%{x.lstrip("^").rstrip("$")}%'},
    '$eq': lambda x: {'eq': x},
    '$neq': lambda x: {'neq': x},
    '$exists': lambda x: {'exists': x},
    '$in': lambda x: {'in': x},
    '$not_in': lambda x: {'not_in': x},
    '$lt': lambda x: {'lt': _value_converter(x)},
    '$gt': lambda x: {'gt': _value_converter(x)},
    '$lte': lambda x: {'lte': _value_converter(x)},
    '$gte': lambda x: {'gte': _value_converter(x)},
    '$not': lambda x: _build_value(x, reverse=True),
    '$size': lambda x: {'size': x},
    '$overlap': lambda x: {'overlap': x if isinstance(x, list) else [x]},
    '$no_overlap': lambda x: {'no_overlap': x if isinstance(x, list) else [x]},
    '$contains_regex': lambda x: {'contains_regex': f'%{x.lstrip("^").rstrip("$")}%'}

}

# When $not is received we swap the operator to it's reversed state
REVERSE_OPERATORS = {
    '$eq': '$neq',
    '$lt': '$gte',
    '$lte': '$gt',
    '$gte': '$lt',
    '$gt': '$lte',
    '$in': '$not_in',
    '$regex': '$not_regex',
    '$overlap': '$no_overlap'
}

# Special key methods, this is done for inner document keys that have been turned to relations
SIMPLE_TO_RELATION = {
    'adapter_properties': lambda k, v: {'adapter': {'properties': _build_value(v, operator_override='$overlap',
                                                                               reverse=('$not' in v))}},
}

# Special cases changes the way we query in certain scenarios, the key must be a full key, and the function
# must return a dict if successful, or None if not.
SPECIAL_CASES = {
    'specific_data.data.hostname':
        lambda v: {'hostnames': VALUE_COMPARISON_METHODS['$contains_regex'](v['$regex'])} if '$regex' in v else None
}


class GqlObject(str):
    """
     GqlObject is an Object in GraphQL terms and we need to open a new {} and add the fields
     """


class GqlField(str):
    """
    GqlField means that given string is a normal field and not an object
    """
    def __new__(cls, value, builder=None):
        obj = str.__new__(cls, value)
        obj.builder = builder
        return obj


class GqlNotSupported(str):
    """
    GqlNotSupported will skip the field but won't crash the query
    """


BUILDER_CONVERTERS = {
    'adapterDevices': GqlObject('adapterDevices'),
    'adapterUsers': GqlObject('adapterUsers'),
    'adapters': GqlField('adapterNames'),
    'os': GqlObject('os'),
    'network_interfaces': GqlObject('interfaces'),
    # For now until labels are supported for both users and devices
    'labels': GqlNotSupported('tags.name'),
    'tags': GqlObject('tags'),
    'is_admin': GqlField('admin'),
    'is_suspended': GqlField('suspended'),
    'is_local': GqlField('local'),
    'is_delegated_admin': GqlField('delegatedAdmin'),
    'is_mfa_enforced': GqlField('mfaEnforced'),
    'is_mfa_enrolled': GqlField('mfaEnrolled'),
    'is_disabled': GqlField('disabled'),
    'account_disabled': GqlField('disabled'),
    'is_locked': GqlField('locked'),
    'ips': GqlField('ipAddrs'),
    'mac': GqlField('macAddr'),
    'image': GqlNotSupported('image'),
    'vlan_list': GqlObject('vlans'),
    'user_created': GqlField('creationDate'),
    'last_bad_logon': GqlField('lastBadLogon'),
    'password_not_required': GqlField('passwordRequired', builder=lambda x: {'eq': not x}),
    'password_never_expires': GqlField('passwordExpires', builder=lambda x: {'eq': not x}),
    'adapter_list_length': GqlField('adapterCount')
}


class Translator:
    """
    The Translator class handle translating AQL into SqlGen (GraphQL) and Projection into a GraphQL projection
    """

    def __init__(self, entity_type: EntityType):
        self._entity_type = entity_type
        self._specific_data_converter = 'adapterDevices' if entity_type == EntityType.Devices else 'adapterUsers'
        self._bool_exp_type = 'device' if entity_type == EntityType.Devices else 'user'

    @cached(cache=LFUCache(maxsize=64), key=lambda _, aql: hash(aql))
    def translate(self, aql):
        """
        Translate AQL to SqlGen filter, use cached to hash already translated AQLs
        """
        processed_aql = process_filter(aql, None)
        tokenized_aql = _pql.find(processed_aql)
        return self._translate_aql(tokenized_aql)

    @cached(cache=LFUCache(maxsize=64), key=lambda _, fields_query: hash(fields_query))
    def build_gql(self, fields_query: str):
        """
        Translate Projection into GraphQL projection, use cached to hash already translated projections
        """
        fields = fields_query.split(',')
        gql = GqlQuery().query(
            name=self._entity_type.name.lower(),
            input={'where': '$where', 'limit': '$limit', 'offset': '$offset', 'orderBy': '$orderBy'})
        gql = gql.operation('query', name='GQLQuery',
                            input={'$where': f'{self._bool_exp_type}_bool_exp!',
                                   '$limit': 'Int = 20',
                                   '$offset': 'Int = 0',
                                   '$orderBy': f'[{self._bool_exp_type}_order_by!]'}
                            )
        # Always add these fields no matter projection
        gql.add_fields('adapterCount', 'id', '_compatibilityAPI')
        created_gql = {}
        for field in fields:
            self._parse_field(field, created_gql, gql)
        return gql.generate()

    def _parse_field(self, field: str, created_gql: dict, current: GqlQuery):
        """
        Parse each field adding them into the current GqlQuery. Since projection can go into inner fields i.e if we want
        to project a devices' adapter_devices or an adapter_devices' os, we will uses created_gql to keep track
        of all gql objected we made.
        """
        if field.startswith('specific_data.data'):
            field = field.replace('specific_data.data', self._specific_data_converter)

        # split the field
        if '.' not in field:
            gql_field = BUILDER_CONVERTERS.get(field, GqlField(field))
            if isinstance(gql_field, GqlObject):
                self._parse_field(gql_field, created_gql, current)
                return
            if isinstance(gql_field, GqlNotSupported):
                return
            current.add_fields(_to_lower_camel_case(gql_field))
            return

        _type, rest = field.split('.', 1)
        gql_field = BUILDER_CONVERTERS.get(_type)
        if not gql_field:
            raise NotImplementedError(f'Unknown {_type}')

        gql = created_gql.get(gql_field)
        if not gql:
            gql = GqlQuery(name=gql_field)
            created_gql[gql_field] = gql
            current.add_fields(gql)
        self._parse_field(rest, created_gql, gql)

    # ============================================ AQL Translation ================================================= #

    def _translate_aql(self, tokenized_aql: typing.Dict) -> typing.Dict:
        """
        Translate an tokenized AQL going over each Key,Value
        """
        gql = {}
        for k, v in tokenized_aql.items():
            # if the key is a Logical operator move to translate Logical, otherwise build comparison on field.
            if k in [AQL_LOGICAL_AND, AQL_LOGICAL_OR]:
                gql.update(self._translate_logical_aql(k, v))
            else:
                gql.update(self._build_comparison(k, v))
        return gql

    def _translate_logical_aql(self, logical_type: typing.AnyStr, value: typing.List[typing.Dict]) -> typing.Dict:
        """
        A Logical AQL is usually a list of tokenized AQLs we would like to translate them all and add them into
        single SqlGen logical term.
        """
        converted_values = []
        for item in value:
            converted_values.append(self._translate_aql(item))
        return {LOGICAL_TERM_CONVERTER[logical_type]: converted_values}

    def _build_comparison(self, key: typing.AnyStr, value: typing.Dict) -> typing.Dict:
        """
        Build comparison from given key and value, the value holds the operator and value for given key
        i.e field: {regex: 'test'}.

        Fields are not always named the same in mongo and PostgreSQL so conversions are used.

        In most cases the field complex with dot separated inner document selections in mongo, in these cases
        we either split and build the nested SqlGen filter or use special cases.

        """
        if key in SPECIAL_CASES:
            r = SPECIAL_CASES[key](value)
            if r:
                return r

        if key.startswith('specific_data.data'):
            return {
                self._specific_data_converter: self._build_comparison(key.split('.', 2)[-1], value)
            }
        # adapter_data is a special case
        if key.startswith('adapters_data'):
            return self._build_adapter_comparison(key.split('.', 1)[-1], value)

        method = SIMPLE_TO_RELATION.get(key)
        if method:
            return method(key, value)
        try:
            prefix, suffix = key.split('.', 1)
        except ValueError:
            gql = BUILDER_CONVERTERS.get(key, GqlField(_to_lower_camel_case(key)))
            return {gql: gql.builder(value) if gql.builder else _build_value(value)}

        converted = BUILDER_CONVERTERS.get(prefix, GqlField(prefix))
        if isinstance(converted, GqlObject):
            return {converted: self._build_comparison(suffix, value)}

        raise NotImplementedError(f'Unknown {key} : {value}')

    def _build_adapter_comparison(self, key, value):
        adapter_type, prop = key.split('.')
        if prop == 'id':
            return {self._specific_data_converter: {'adapterName': {'eq': adapter_type}}}
        return {self._specific_data_converter: {'adapterName': {'eq': adapter_type}, prop: _build_value(value)}}


# ====================================== Private Methods ====================================== #

def _to_lower_camel_case(snake_str):
    """
    Fields in GraphQL projection are usually lowerCamelCase
    """
    if '_' not in snake_str:
        return snake_str
    first, *others = snake_str.split('_')
    return ''.join([first.lower(), *map(str.title, others)])


def _get_op_method(operator, reverse=False):
    if reverse:
        return VALUE_COMPARISON_METHODS.get(REVERSE_OPERATORS.get(operator))
    return VALUE_COMPARISON_METHODS.get(operator)


def _build_value(value: typing.Dict, operator_override=None, reverse=False):
    """
    Builds value based on given operator. use operator override to use a different method
    and reverse to reverse the operator
    """
    if not isinstance(value, dict) and operator_override is None:
        return {'eq': _value_converter(value)}

    if operator_override is not None:
        method = _get_op_method(operator_override, reverse=reverse)
        return method(value)

    for k in value.keys():
        method = _get_op_method(k, reverse=reverse)
        if not method:
            continue
        return method(value[k])
    raise NotImplementedError(value)


def _value_converter(x):
    if isinstance(x, datetime.datetime):
        return int(x.timestamp() * 1000)
    return x
