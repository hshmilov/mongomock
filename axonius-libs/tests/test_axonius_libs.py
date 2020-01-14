from axonius.utils.parsing import figure_out_os


def test_figure_out_os():
    assert figure_out_os('Microsoft Windows Server 2016 (64-bit)') == {'type': 'Windows', 'distribution': 'Server 2016',
                                                                       'bitness': 64,
                                                                       'os_str':
                                                                           'Microsoft Windows '
                                                                           'Server 2016 (64-bit)'.lower()}
    assert figure_out_os('Canonical, Ubuntu, 16.04 LTS') == {'type': 'Linux', 'distribution': 'Ubuntu',
                                                             'bitness': None,
                                                             'os_str': 'Canonical, Ubuntu, 16.04 LTS'.lower()}
    assert figure_out_os('iphone') == {'type': 'iOS', 'distribution': None, 'bitness': None,
                                       'os_str': 'iphone'.lower()}
    assert figure_out_os('os x, x64') == {'type': 'OS X', 'distribution': None, 'bitness': 64,
                                          'os_str': 'os x, x64'.lower()}
    assert figure_out_os('android, amd64') == {'type': 'Android', 'distribution': None, 'bitness': 64,
                                               'os_str': 'android, amd64'.lower()}
