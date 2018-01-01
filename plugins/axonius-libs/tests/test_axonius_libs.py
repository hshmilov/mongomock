import logging
import axonius.parsing_utils


def test_figure_out_os():
    assert axonius.parsing_utils.figure_out_os('Microsoft Windows Server 2016 (64-bit)') == {'type': 'Windows',
                                                                                             'distribution': 'Server 2016',
                                                                                             'bitness': 64}
    assert axonius.parsing_utils.figure_out_os('Canonical, Ubuntu, 16.04 LTS') == {'type': 'Linux',
                                                                                   'distribution': 'Ubuntu',
                                                                                   'bitness': None}
    assert axonius.parsing_utils.figure_out_os('iphone') == {'type': 'iOS',
                                                             'distribution': None,
                                                             'bitness': None}
    assert axonius.parsing_utils.figure_out_os('os x, x64') == {'type': 'OS X',
                                                                'distribution': None,
                                                                'bitness': 64}
    assert axonius.parsing_utils.figure_out_os('android, amd64') == {'type': 'Android',
                                                                     'distribution': None,
                                                                     'bitness': 64}
