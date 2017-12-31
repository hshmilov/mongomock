def run_in_executor_helper(executor, method_to_call, resolve, reject):
    """
    Helps with running Promises in an executor
    :param executor: executor to run on
    :param method_to_call: method to run
    :param resolve: will be called if method returns
    :param reject: will be called with exception from method
    :return:
    """

    def resolver():
        try:
            resolve(method_to_call())
        except Exception as e:
            reject(e)

    executor.submit(resolver)
