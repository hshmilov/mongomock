from logging import INFO


def log_metric(logger, metric_name, metric_value, adapter=None):
    extra = {'metric_name': metric_name, 'value': metric_value}
    if adapter:
        extra['adapter'] = adapter
    logger.log(INFO, 'METRIC', extra=extra)
