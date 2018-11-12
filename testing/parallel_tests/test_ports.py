from services.ports import DOCKER_PORTS


def test_ports():
    assert len(set(DOCKER_PORTS.values())) == len(DOCKER_PORTS)
    for port in DOCKER_PORTS.values():
        assert port < 32768, 'Can not allow any port above that, since this is not vpc-acl-allowed in case of demo\'s!'
