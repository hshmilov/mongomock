def initialize_fixture(request, service):
    service.take_process_ownership()
    service.stop(should_delete=True)
    service.start_and_wait()

    def fin():
        service.stop(should_delete=True)

    request.addfinalizer(fin)
