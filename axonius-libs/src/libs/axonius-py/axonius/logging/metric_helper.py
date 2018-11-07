import numbers
from logging import INFO


def log_metric(logger, metric_name, metric_value, adapter=None):
    if not isinstance(metric_value, numbers.Number):
        metric_value = str(metric_value)
    extra = {'metric_name': metric_name, 'value': metric_value}
    if adapter:
        extra['adapter'] = adapter
    logger.log(INFO, 'METRIC', extra=extra)
