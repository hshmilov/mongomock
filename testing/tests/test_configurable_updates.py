from axonius.mixins.configurable import Configurable

# just so we can whitebox configurable
# pylint: disable=W0212


def run_configurable_upgrade(new_schema, old_data, default_data) -> dict:
    return Configurable._Configurable__try_automigrate_config_schema(new_schema, old_data, default_data)


def check_dict_subset(bigdict, subset):
    """
    Raises if there is a value that is not a dict in `subset` or any dict inside `subset` (lists unsupported)
    that isn't present in `bigdict` or has a different value then the respectful value in `bigdict`
    """
    if bigdict == subset:
        return

    assert bigdict
    assert isinstance(bigdict, dict)

    for k, v in subset.items():
        check_dict_subset(v, bigdict.get(k))


def test_null_upgrade():
    schema = {
        'items': [
            {
                'name': 'x',
                'type': 'number'
            }
        ],
        'type': 'array'
    }

    processed_data = run_configurable_upgrade(schema,
                                              old_data={'x': 10},
                                              default_data={'x': 1})
    check_dict_subset(processed_data,
                      {'x': 10})


def test_simple_upgrade():
    """
    Test where one field was added
    """
    schema = {
        'items': [
            {
                'name': 'x',
                'type': 'number'
            },
            {
                'name': 'y',
                'type': 'number'
            }
        ],
        'type': 'array'
    }

    processed_data = run_configurable_upgrade(schema,
                                              old_data={'x': 10},
                                              default_data={'x': 123123, 'y': 2})
    check_dict_subset(processed_data,
                      {'x': 10, 'y': 2})


def test_field_renamed():
    """
    Test where one field renamed
    """
    schema = {
        'items': [
            {
                'name': 'y',
                'type': 'number'
            }
        ],
        'type': 'array'
    }

    processed_data = run_configurable_upgrade(schema,
                                              old_data={'x': 10},
                                              default_data={'y': 2})

    check_dict_subset(processed_data,
                      {'y': 2})


def test_field_to_array():
    """
    Test where one field turned into an array
    """
    schema = {
        'items': [
            {
                'name': 'x',
                'type': 'array',
                'items': [
                    {
                        'name': 'y',
                        'type': 'number'
                    }
                ]
            },
            {
                'name': 'y',
                'type': 'number',
            }
        ],
        'type': 'array'
    }

    processed_data = run_configurable_upgrade(schema,
                                              old_data={'x': 10, 'y': 3},
                                              default_data={
                                                  'x':
                                                      {
                                                          'y': 15
                                                      },
                                                  'y': 123123
                                              }
                                              )

    check_dict_subset(processed_data,
                      {
                          'x':
                              {
                                  'y': 15
                              },
                          'y': 3
                      })


def test_array_to_field():
    """
    Test where one array turned into a field
    """
    schema = {
        'items': [
            {
                'name': 'x',
                'type': 'number',
            }
        ],
        'type': 'array'
    }

    processed_data = run_configurable_upgrade(schema,
                                              old_data={
                                                  'x': {
                                                      'y': 5
                                                  }
                                              },
                                              default_data={
                                                  'x': 10
                                              }
                                              )

    check_dict_subset(processed_data,
                      {
                          'x': 10
                      })


def test_field_added_in_array():
    """
    Test where one field turned into an array
    """
    schema = {
        'items': [
            {
                'name': 'x',
                'type': 'array',
                'items': [
                    {
                        'name': 'y',
                        'type': 'number'
                    },
                    {
                        'name': 'z',
                        'type': 'number'
                    }
                ]
            }
        ],
        'type': 'array'
    }

    processed_data = run_configurable_upgrade(schema,
                                              old_data={
                                                  'x':
                                                      {
                                                          'y': 20
                                                      }
                                              },
                                              default_data={
                                                  'x':
                                                      {
                                                          'y': 123123,
                                                          'z': 16
                                                      }
                                              }
                                              )

    check_dict_subset(processed_data,
                      {
                          'x':
                              {
                                  'y': 20,
                                  'z': 16
                              }
                      })
