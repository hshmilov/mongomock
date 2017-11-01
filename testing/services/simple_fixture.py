def initalize_fixture(request, service):
    service.start()
    service.wait_for_service()

    def fin():
        service.stop()

    request.addfinalizer(fin)
