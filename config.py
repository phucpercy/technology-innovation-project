import os


_CONFIGURATION = {
    "S3_BUCKET_NAME" : "tip-monitoring-url-resources",
    "URL_FILE_NAME" : "urls.json",
    "SNS_TOPIC_NAME" : "MonitoringAbnormal",
    "MONITOR_INTERVAL_SECONDS" : 60,
    "METRICS_NAMESPACE": "Monitor",
    "DYNAMO_TABLE_NAME": "MonitoringAlarm",
}

def _setup():
    default_types = [type(v) for v in _CONFIGURATION.values()]

    for k, t in zip(_CONFIGURATION.keys(), default_types):
        if os.getenv(k) is not None:
            _CONFIGURATION[k] = t(os.environ[k])
        print(f"{k} = {_CONFIGURATION[k]}")
    globals().update(_CONFIGURATION)

_setup()
