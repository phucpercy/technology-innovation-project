import os


_CONFIGURATION = {
    "S3_BUCKET_NAME" : "tip-monitoring-url-resources",
    "URL_FILE_NAME" : "urls.json",
    "SNS_TOPIC_NAME" : "MonitoringAbnormal",
    "MONITOR_INTERVAL_SECONDS" : 60,
    "METRICS_NAMESPACE": "Monitor",
    "DYNAMO_TABLE_NAME": "MonitoringAlarm",
    "SUBSCRIPTION_EMAIL_LIST": ["phucpercy@gmail.com"],
    "SENDER_EMAIL": "xmanphuc@gmail.com"
}

_TYPE_CAST_FUNCTION_MAP = {
    list: lambda x: x.split(",")
}

def _setup():
    default_types = [type(v) for v in _CONFIGURATION.values()]

    for k, t in zip(_CONFIGURATION.keys(), default_types):
        if os.getenv(k) is not None:
            cast_func = _TYPE_CAST_FUNCTION_MAP.get(t, t)
            _CONFIGURATION[k] = cast_func(os.environ[k])
        print(f"{k} = {_CONFIGURATION[k]}")
    globals().update(_CONFIGURATION)

_setup()
