def initialize_fixture(request, service):
    service.start_and_wait()

    def fin():
        service.stop()

    request.addfinalizer(fin)
