import json
import re
import os
import hashlib
import concurrent.futures

import boto3
import boto3.exceptions
import boto3.s3
import boto3.s3.constants
from web_measurer.webpage import WebPage


STUB_JSON = '''{
  "urls": [
    {
      "url": "https://www.swinburne.edu.au",
      "name": "Swinburne University Website",
      "metrics": [
        {"type": "Availability", "threshold": "<1"},
        {"type": "Page Time", "threshold": ">=0.5"},
        {"type": "Page Size", "threshold": "<178939,>178939"}
      ]
    },
    {
      "url": "https://eca.edu.au",
      "name": "ECA Website",
      "metrics": [
        {"type": "Availability", "threshold": "<1"},
        {"type": "Page Time", "threshold": ">=0.5"},
        {"type": "Page Size", "threshold": "<81165,>81165"}
      ]
    },
    {
      "url": "https://www.bbc.com/news",
      "name": "BBC News Website",
      "metrics": [
        {"type": "Availability", "threshold": "<1"},
        {"type": "Page Time", "threshold": ">=0.5"},
        {"type": "Page Size", "threshold": "<299261,>299261"}
      ]
    }
  ]
}
'''

METRIC_UNIT_MAP = {
    'Availability': 'None', 'Page Time': 'Seconds', 'Page Size': 'Bytes'
}


def parse_threshold_expression(express: str):
    if len(express) == 0:
        return []

    op_map = {
        "<": "LessThanThreshold",
        ">": "GreaterThanThreshold",
        "<=": "LessThanOrEqualToThreshold",
        ">=": "GreaterThanOrEqualToThreshold",
    }

    exps = express.split(',')
    thresholds = []
    for exp in exps:
        exp = exp.strip()
        regex = re.compile(r"[><]=?")
        m = regex.match(exp)
        if m is None:
            raise RuntimeError(f"'{express}' is not a valid threshold expression.")
        compare_op = m.group(0)
        threshold = float(exp[len(compare_op):])
        op = op_map[compare_op]
        thresholds.append((exp, op, threshold))

    return thresholds


def retrieve_url_resources(s3_bucket_name, filename):
    s3_client = boto3.client('s3')

    try:
        response = s3_client.get_object(Bucket=s3_bucket_name, Key=filename)
    except s3_client.exceptions.NoSuchKey:
        return json.loads(STUB_JSON)

    object_content = response['Body'].read().decode('utf-8')
    url_resources = json.loads(object_content)

    return url_resources


def download_page(url):
    page = WebPage(url)
    page.download_page()
    return page


def monitor_pages(urls):
    data = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(download_page, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                page = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (url, exc))
            else:
                print(
                    f'{url}\tavailability={page.availability}\tsize={format(page.page_size, "_")}\telapsed={page.time_elapsed:0.2f}secs')
                data[page.url] = {
                    'Availability': 1 if page.availability else 0,
                    'Page Size': page.page_size,
                    'Page Time': page.time_elapsed
                }

    return data


def push_dashboard(dashboard_name, url_resources, namespace, period):
    max_width = 24
    metric_width = 6
    metric_height = 4

    cur_x = 0
    cur_y = 0
    cur_h = 0

    def update_position(body, width, height):
        nonlocal cur_x, cur_y, cur_h
        if cur_x + width > max_width:
            cur_y += cur_h
            cur_h = 0
            cur_x = 0
        body["x"] = cur_x
        body["y"] = cur_y
        cur_x += width
        cur_h = max(cur_h, height)

    def create_text_widget(markdown, width, height):
        body = {
            "type": "text",
            "width": width,
            "height": height,
            "properties": {
                "markdown": markdown
            }
        }
        update_position(body, width, height)
        return body

    def create_metric_widget(metrics, width, height, period):
        body = {
            "type": "metric",
            "width": width,
            "height": height,
            "properties": {
                "view": "timeSeries",
                "region": "",
                "metrics": [
                    [
                        *metrics,
                        {
                            "period": period
                        }
                    ]
                ],
                "yAxis": {}
            }
        }
        update_position(body, width, height)
        return body
    
    widgets = []
    widgets.append(create_text_widget("# Web Monitor Dashboard", max_width, 1))
    for url_conf in url_resources['urls']:
        widgets.append(create_text_widget(f'## {url_conf["name"]}', max_width, 1))
        for metric_conf in url_conf['metrics']:
            widgets.append(
                create_metric_widget(
                    [namespace, metric_conf['type'], "URL", url_conf['url']],
                    metric_width,
                    metric_height,
                    period
                )
            )
    dashboard_body = json.dumps({"widgets": widgets})
    cloudwatch = boto3.client('cloudwatch')
    cloudwatch.put_dashboard(
        DashboardName=dashboard_name,
        DashboardBody=dashboard_body
    )


def get_existing_alarm_names(namespace):
    cloudwatch = boto3.client('cloudwatch')
    response = cloudwatch.describe_alarms(
        AlarmNamePrefix=f'{namespace}-Alarm-'
    )
    alarm_names = {alarm['AlarmName'] for alarm in response['MetricAlarms']}
    return alarm_names


def remove_alarms(existing_alarm_names, new_alarm_names):
    cloudwatch = boto3.client('cloudwatch')
    alarm_names = list(existing_alarm_names - new_alarm_names)
    if len(alarm_names) > 0:
        cloudwatch.delete_alarms(AlarmNames=alarm_names)


def push_alarms(url_resources, namespace, topic_arn, period, existing_alarm_names):
    cloudwatch = boto3.client('cloudwatch')
    new_alarm_names = set()
    for url_conf in url_resources['urls']:
        url = url_conf['url']
        for metric_conf in url_conf['metrics']:
            metric_type = metric_conf['type']
            threshold_exp = metric_conf['threshold']
            thresholds = parse_threshold_expression(threshold_exp)
            for exp, op, threshold in thresholds:
                hashdata = f'{namespace}{metric_type}{url}{exp}'
                hashtag = hashlib.shake_128(hashdata.encode()).hexdigest(5)
                alarm_name = f'{namespace}-Alarm-{metric_type}-{url}-{hashtag}'
                new_alarm_names.add(alarm_name)
                if alarm_name in existing_alarm_names:
                    continue
                cloudwatch.put_metric_alarm(
                    AlarmName=alarm_name,
                    AlarmActions=[
                        topic_arn,
                    ],
                    MetricName=metric_type,
                    Namespace=namespace,
                    Statistic='Average',
                    Dimensions=[
                        {
                            'Name': 'URL',
                            'Value': url
                        },
                    ],
                    Period=period,
                    EvaluationPeriods=1,
                    DatapointsToAlarm=1,
                    Threshold=threshold,
                    ComparisonOperator=op
                )

    return new_alarm_names


def push_metrics(data, url_resources, namespace):
    metric_data = []
    for url_conf in url_resources['urls']:
        url = url_conf['url']
        for metric_conf in url_conf['metrics']:
            metric_type = metric_conf['type']
            metric = {
                'MetricName': metric_type,
                'Unit': METRIC_UNIT_MAP[metric_type],
                'Dimensions': [
                    {
                        'Name': 'URL',
                        'Value': url
                    }
                ],
                'Value': data[url][metric_type]
            }
            metric_data.append(metric)

    cloudwatch = boto3.client('cloudwatch')
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=metric_data
    )


def measuring_handler(event, context):
    # get environment variables
    s3_bucket_name = os.environ["S3_BUCKET_NAME"]
    url_filename = os.environ["URL_FILE_NAME"]
    namespace = os.environ["METRICS_NAMESPACE"]
    dashboard_name = os.environ["CLOUDWATCH_DASHBOARD_NAME"]
    period = int(os.environ["MONITOR_INTERVAL_SECONDS"])
    topic_arn = os.environ["TOPIC_ARN"]

    # collect metrics data
    url_resources = retrieve_url_resources(s3_bucket_name, url_filename)
    urls = []
    for i in url_resources['urls']:
        urls.append(i['url'])
    metric_data = monitor_pages(urls)

    # update dashboard and alarms
    existing_alarm_names = get_existing_alarm_names(namespace)
    new_alarm_names = push_alarms(url_resources, namespace, topic_arn, period, existing_alarm_names)
    remove_alarms(existing_alarm_names, new_alarm_names)
    is_update = existing_alarm_names != new_alarm_names
    if is_update:
        push_dashboard(dashboard_name, url_resources, namespace, period)

    push_metrics(metric_data, url_resources, namespace)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(metric_data)
    }

def test(s3_bucket_name, url_filename):
    url_resources = retrieve_url_resources(s3_bucket_name, url_filename)
    urls = []
    for i in url_resources['urls']:
        urls.append(i['url'])
    metric_data = monitor_pages(urls)

    print(metric_data)
