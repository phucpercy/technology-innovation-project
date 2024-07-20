import os

_CONFIGURATION = {
    "S3_BUCKET_NAME" : "tip-monitoring-url-resources",
    "URL_FILE_NAME" : "urls.json",
    "SNS_TOPIC_NAME" : "MonitoringAbnormal",
    "MONITOR_INTERVAL_SECONDS" : 60,
    "MONITOR_LAMBDA_TIMEOUT_SECONDS": 10,
    "METRICS_NAMESPACE": "Monitor",
    "DYNAMO_ALARM_TABLE_NAME": "MonitoringAlarm",
    "DYNAMO_RESOURCES_TABLE_NAME": "MonitoringResources",
    "SUBSCRIPTION_EMAIL_LIST": ["phucpercy@gmail.com"],
    "SENDER_EMAIL": "xmanphuc@gmail.com",
    "REPO_PATH": "phucpercy/technology-innovation-project",
    "REPO_BRANCH": "main",
    "REPO_SECRET_KEY_ID": "my-github-token"
}

_TYPE_CAST_FUNCTION_MAP = {
    list: lambda x: [] if len(x) == 0 else x.split(",")
}

_TYPE_CAST_BACKWARD_FUNCTION_MAP = {
    list: lambda x: ",".join(x)
}


def export_env():
    envs = {}
    for k, v in _CONFIGURATION.items():
        cast_func = _TYPE_CAST_BACKWARD_FUNCTION_MAP.get(type(v), str)
        envs[k] = cast_func(v)

    return envs


def _setup():
    default_types = [type(v) for v in _CONFIGURATION.values()]

    for k, t in zip(_CONFIGURATION.keys(), default_types):
        if os.getenv(k) is not None:
            cast_func = _TYPE_CAST_FUNCTION_MAP.get(t, t)
            _CONFIGURATION[k] = cast_func(os.environ[k])
        print(f"{k} = {_CONFIGURATION[k]}")
    globals().update(_CONFIGURATION)

_setup()
