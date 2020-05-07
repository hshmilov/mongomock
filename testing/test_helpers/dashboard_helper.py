def assert_asc_sort_by_value(chart_values):
    previous_value = chart_values[0]
    for value in chart_values[1:]:
        assert int(value) >= int(previous_value)
        previous_value = value


def assert_desc_sort_by_value(chart_values):
    previous_value = chart_values[0]
    for value in chart_values[1:]:
        assert value <= previous_value
        previous_value = value


def assert_asc_sort_by_name(chart_values):
    previous_value = chart_values[0].lower()
    for value in chart_values[1:]:
        assert value.lower() >= previous_value
        previous_value = value.lower()


def assert_desc_sort_by_name(chart_values):
    previous_value = chart_values[0].lower()
    for value in chart_values[1:]:
        assert value.lower() <= previous_value
        previous_value = value.lower()
