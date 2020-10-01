from axonius.utils.parsing import figure_out_os


def test_windows_os():
    data = {
        'Microsoft Windows [Version 10.0.17134.829]':
            {'type': 'Windows', 'distribution': '10', 'type_distribution': 'Windows 10',
             'bitness': None, 'is_windows_server': False,
             'os_str': 'Microsoft Windows [Version 10.0.17134.829]'.lower()},
        'Microsoft Windows Storage Server 2008 R2 Standard':
            {'type': 'Windows', 'distribution': 'Server 2008', 'type_distribution': 'Windows Server 2008',
             'bitness': None, 'is_windows_server': True,
             'os_str': 'Microsoft Windows Storage Server 2008 R2 Standard'.lower()},
        'Microsoft Windows Server 2012 R2 Standard':
            {'type': 'Windows', 'distribution': 'Server 2012', 'type_distribution': 'Windows Server 2012',
             'bitness': None, 'is_windows_server': True,
             'os_str': 'Microsoft Windows Server 2012 R2 Standard'.lower()},
        'Microsoft Windows 8.1 Pro':
            {'type': 'Windows', 'distribution': '8.1', 'type_distribution': 'Windows 8.1',
             'bitness': None, 'is_windows_server': False,
             'os_str': 'Microsoft Windows 8.1 Pro'.lower()},
        'Microsoft Windows Server 2012 R2 x64 Server Standard (6.3.9600)':
            {'type': 'Windows', 'distribution': 'Server 2012 R2', 'type_distribution': 'Windows Server 2012 R2',
             'bitness': 64, 'is_windows_server': True,
             'os_str': 'Microsoft Windows Server 2012 R2 x64 Server Standard (6.3.9600)'.lower()},
        'Microsoft Windows Server 2008 R2 x64 Server Standard Service Pack 1 (6.1.7601)':
            {'type': 'Windows', 'distribution': 'Server 2008 R2', 'type_distribution': 'Windows Server 2008 R2',
             'bitness': 64, 'is_windows_server': True,
             'os_str': 'Microsoft Windows Server 2008 R2 x64 Server Standard Service Pack 1 (6.1.7601)'.lower()},
        'Microsoft Windows 2016 Server x64 Server Standard (10.0.14393)':
            {'type': 'Windows', 'distribution': 'Server 2016', 'type_distribution': 'Windows Server 2016',
             'bitness': 64, 'is_windows_server': True,
             'os_str': 'Microsoft Windows 2016 Server x64 Server Standard (10.0.14393)'.lower()},
        'Microsoft Windows Server 2019 Standard Evaluation':
            {'type': 'Windows', 'distribution': 'Server 2019', 'type_distribution': 'Windows Server 2019',
             'bitness': None, 'is_windows_server': True,
             'os_str': 'Microsoft Windows Server 2019 Standard Evaluation'.lower()},
        'Windows 95': {'type': 'Windows', 'distribution': '95', 'type_distribution': 'Windows 95',
                       'bitness': None, 'is_windows_server': False,
                       'os_str': 'Windows 95'.lower()},
        '13 - inch Retina MacBook Pro': {'type': 'OS X', 'distribution': None, 'bitness': None,
                                         'os_str': '13 - inch Retina MacBook Pro'.lower()},
        'mac os 10 (os/x)': {'type': 'OS X', 'distribution': None, 'bitness': None,
                             'os_str': 'mac os 10 (os/x)'.lower()},
        'mac os 10.14 (os/x)': {'type': 'OS X', 'distribution': '10.14', 'type_distribution': 'OS X 10.14',
                                'bitness': None, 'os_str': 'mac os 10.14 (os/x)'.lower()},
        'mac os 10.14(os/x)': {'type': 'OS X', 'distribution': '10.14', 'type_distribution': 'OS X 10.14',
                               'bitness': None, 'os_str': 'mac os 10.14(os/x)'.lower()},
        'mac os 10.14. (os/x)': {'type': 'OS X', 'distribution': '10.14', 'type_distribution': 'OS X 10.14',
                                 'bitness': None, 'os_str': 'mac os 10.14. (os/x)'.lower()},
        'mac os 10.14.4 (os/x)': {'type': 'OS X', 'distribution': '10.14.4', 'type_distribution': 'OS X 10.14.4',
                                  'bitness': None, 'os_str': 'mac os 10.14.4 (os/x)'.lower()},
        'mac os 10.14.4. (os/x)': {'type': 'OS X', 'distribution': '10.14.4', 'type_distribution': 'OS X 10.14.4',
                                   'bitness': None, 'os_str': 'mac os 10.14.4. (os/x)'.lower()},
        'mac mac os x 10.14.6': {'type': 'OS X', 'distribution': '10.14.6', 'type_distribution': 'OS X 10.14.6',
                                 'bitness': None, 'os_str': 'mac mac os x 10.14.6'.lower()},
        'mac os x 10.12.62 x86_64': {'type': 'OS X', 'distribution': '10.12.62', 'type_distribution': 'OS X 10.12.62',
                                     'bitness': 64, 'os_str': 'mac os x 10.12.62 x86_64'.lower()},
        'mac os x 10.12.62.1 x86_64': {'type': 'OS X', 'distribution': '10.12.62.1',
                                       'type_distribution': 'OS X 10.12.62.1', 'bitness': 64,
                                       'os_str': 'mac os x 10.12.62.1 x86_64'.lower()},
        'mac os 11 (os/x)': {'type': 'OS X', 'distribution': None, 'bitness': None,
                             'os_str': 'mac os 11 (os/x)'.lower()},
        'mac os 11. (os/x)': {'type': 'OS X', 'distribution': None, 'bitness': None,
                              'os_str': 'mac os 11. (os/x)'.lower()},
        'macbook 11.0': {'type': 'OS X', 'distribution': '11.0', 'type_distribution': 'OS X 11.0',
                         'bitness': None, 'os_str': 'macbook 11.0'.lower()},
        'macbook 10.16': {'type': 'OS X', 'distribution': '10.16', 'type_distribution': 'OS X 10.16',
                          'bitness': None, 'os_str': 'macbook 10.16'.lower()},
        'macbook 10.16 ': {'type': 'OS X', 'distribution': '10.16', 'type_distribution': 'OS X 10.16',
                           'bitness': None, 'os_str': 'macbook 10.16'.lower()},
        'macbook 10.16.3': {'type': 'OS X', 'distribution': '10.16.3', 'type_distribution': 'OS X 10.16.3',
                            'bitness': None, 'os_str': 'macbook 10.16.3'.lower()},
        'Microsoft Windows 7 Professional': {'type': 'Windows', 'distribution': '7', 'type_distribution': 'Windows 7',
                                             'bitness': None,
                                             'is_windows_server': False,
                                             'os_str': 'Microsoft Windows 7 Professional'.lower()},
        # - release version format - #
        'Microsoft Windows NT Advanced Server 6.3': {'type': 'Windows', 'distribution': 'Server 2012 R2',
                                                     'type_distribution': 'Windows Server 2012 R2',
                                                     'bitness': None, 'is_windows_server': True,
                                                     'os_str': 'Microsoft Windows NT Advanced Server 6.3'.lower()},

        'Microsoft Windows NT Server 10.0.9999': {'type': 'Windows', 'distribution': 'Server 2019',
                                                  'type_distribution': 'Windows Server 2019',
                                                  'bitness': None,
                                                  'is_windows_server': True,
                                                  'os_str': 'Microsoft Windows NT Server 10.0.9999'.lower()},

        'Microsoft Windows NT Workstation 6.3': {'type': 'Windows', 'distribution': '8.1',
                                                 'type_distribution': 'Windows 8.1',
                                                 'bitness': None,
                                                 'is_windows_server': False,
                                                 'os_str': 'Microsoft Windows NT Workstation 6.3'.lower()},
    }
    for dist, output in data.items():
        assert figure_out_os(dist) == output
