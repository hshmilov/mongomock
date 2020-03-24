from services.plugins.core_service import replace_notification_content_with_hooks
from axonius.consts.core_consts import LINK_REGEX


def test_notification_content_replacement():

    content = [
        'Alert - \"test\" for the following query has been triggered: Managed Devices\n\nAlert Details'
        '\nThe alert was triggered here: https://localhost/devices?view=All+installed+software+on+devices'
        ' because: Manual run\nThe number of here also: https://test.com/testing.js devices returned by '
        'and here: https://test.com/testing.js the query:0\nThe previous number of devices was:0\n\nYou '
        'can view the query and its results here: https://test.com/testing.js',
        'Alert - \"test\" for the following query has been triggered: Managed Devices\n\nAlert Details'
        '\nThe alert was triggered here: https://test.com/testing.js'
        ' because: Manual run\nThe number of here also: https://test.com/testing.js devices returned by '
        'and here: https://test.com/testing.js the query:0\nThe previous number of devices was:0\n\nYou '
        'can view the query and its results here: https://test.com/testing.js',
        'Testing some content without any links']

    expected = [
        'Alert - \"test\" for the following query has been triggered: Managed Devices\n\n'
        'Alert Details\nThe alert was triggered here: {LINK_0} because: Manual run\n'
        'The number of here also: {LINK_1} devices returned by and here: {LINK_1} the '
        'query:0\nThe previous number of devices was:0\n\nYou can view '
        'the query and its results here: {LINK_1}',
        'Alert - \"test\" for the following query has been triggered: Managed Devices\n\n'
        'Alert Details\nThe alert was triggered here: {LINK_0} because: Manual run\n'
        'The number of here also: {LINK_0} devices returned by and here: {LINK_0} the '
        'query:0\nThe previous number of devices was:0\n\nYou can view '
        'the query and its results here: {LINK_0}',
        'Testing some content without any links']

    _, replaced_content = replace_notification_content_with_hooks(content[0], LINK_REGEX)
    assert replaced_content == expected[0]
    _, replaced_content = replace_notification_content_with_hooks(content[1], LINK_REGEX)
    assert replaced_content == expected[1]
    _, replaced_content = replace_notification_content_with_hooks(content[2], LINK_REGEX)
    assert replaced_content == expected[2]
