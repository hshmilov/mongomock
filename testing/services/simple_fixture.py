def initialize_fixture(request, service):
    service.take_process_ownership()
    service.stop(should_delete=True)
    service.start_and_wait()
    if service.should_register_unique_dns:
        service.register_unique_dns()
    request.addfinalizer(lambda: service.stop(should_delete=True))
