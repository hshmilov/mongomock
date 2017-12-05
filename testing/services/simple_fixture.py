def initialize_fixture(request, service):
    service.wait_for_service()

    def fin():
        service.stop()

    request.addfinalizer(fin)
