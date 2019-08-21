from axonius.utils.parsing import figure_out_os


def test_windows_os():
    data = {
        'Microsoft Windows [Version 10.0.17134.829]':
            {'type': 'Windows', 'distribution': '10', 'bitness': None},
        'Microsoft Windows Storage Server 2008 R2 Standard':
            {'type': 'Windows', 'distribution': 'Server 2008', 'bitness': None},
        'Microsoft Windows Server 2012 R2 Standard':
            {'type': 'Windows', 'distribution': 'Server 2012', 'bitness': None},
        'Microsoft Windows 8.1 Pro':
            {'type': 'Windows', 'distribution': '8.1', 'bitness': None},
        'Microsoft Windows Server 2012 R2 x64 Server Standard (6.3.9600)':
            {'type': 'Windows', 'distribution': 'Server 2012', 'bitness': 64},
        'Microsoft Windows Server 2008 R2 x64 Server Standard Service Pack 1 (6.1.7601)':
            {'type': 'Windows', 'distribution': 'Server 2008', 'bitness': 64},
        'Microsoft Windows 2016 Server x64 Server Standard (10.0.14393)':
            {'type': 'Windows', 'distribution': 'Server 2016', 'bitness': 64},
        'Microsoft Windows Server 2019 Standard Evaluation':
            {'type': 'Windows', 'distribution': 'Server 2019', 'bitness': None},
        'Windows 95': {'type': 'Windows', 'distribution': '95', 'bitness': None},
        '13 - inch Retina MacBook Pro': {'type': 'OS X', 'distribution': None, 'bitness': None},
        'Microsoft Windows 7 Professional': {'type': 'Windows', 'distribution': '7', 'bitness': None}

    }
    for dist, output in data.items():
        assert figure_out_os(dist) == output
