from pathlib import Path

SYSCTL_PATH = '/etc/sysctl.conf'


def set_sysctl_value(key, value, path=SYSCTL_PATH):
    key = str(key)
    value = str(value)
    text = Path(path).read_text()
    content = text.split('\n')
    content = [line.strip() for line in content]
    content = [line for line in content if not line.startswith('#') and line]
    values_dict = {}
    for line in content:
        k, v = line.split('=')
        values_dict[k.strip()] = v.strip()

    values_dict[key] = value

    res = '\n'.join([f'{k} = {values_dict[k]}' for k in values_dict])
    Path(path).write_text(res + '\n')
