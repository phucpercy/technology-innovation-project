import json

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
      "metricNames": ["Availability", "Page Time", "Page Size"]
    },
    {
      "url": "https://eca.edu.au",
      "name": "ECA Website",
      "metricNames": ["Availability", "Page Time", "Page Size"]
    },
    {
      "url": "https://www.bbc.com/news",
      "name": "BBC News Website",
      "metricNames": ["Availability", "Page Time", "Page Size"]
    }
  ]
}
'''

METRIC_UNIT_MAP = {
    'Availability': 'None', 'Page Time': 'Seconds', 'Page Size': 'Bytes'
}


def retrieve_url_resources():
    s3_client = boto3.client('s3')

    try:
        response = s3_client.get_object(Bucket='tip-monitoring-url-resources', Key='urls.json')
    except s3_client.exceptions.NoSuchKey:
        return json.loads(STUB_JSON)

    object_content = response['Body'].read().decode('utf-8')
    url_resources = json.loads(object_content)

    return url_resources


def monitor_pages(urls):
    data = {}

    for url in urls:
        page = WebPage(url)
        page.download_page()
        print(
            f'{url}\tavailability={page.availability}\tsize={format(page.page_size, "_")}\telapsed={page.time_elapsed:0.2f}secs')

        data[page.url] = {
            'Availability': 1 if page.availability else 0,
            'Page Size': page.page_size,
            'Page Time': page.time_elapsed
        }

    return data

def push_metrics(data, url_resources):
    # {url: {metric_name1: unit1, metric_name2, unit2}}
    url_metric_confs = {}
    for conf in url_resources['urls']:
        d = {name: METRIC_UNIT_MAP[name] for name in conf['metricNames']}
        url_metric_confs[conf['url']] = d

    metric_data = []
    for url, metric_conf in url_metric_confs.items():
        for metric_name, unit in metric_conf.items():
            metric = {
                'MetricName': metric_name,
                'Unit': unit,
                'Dimensions': [
                    {
                        'Name': 'URL',
                        'Value': url
                    }
                ],
                'Value': data[url][metric_name]
            }
            metric_data.append(metric)

    cloudwatch = boto3.client('cloudwatch')
    cloudwatch.put_metric_data(
        Namespace='Monitor',
        MetricData=metric_data
    )

def measuring_handler(event, context):
    url_resources = retrieve_url_resources()
    urls = []
    for i in url_resources['urls']:
        urls.append(i['url'])
    metric_data = monitor_pages(urls)
    push_metrics(metric_data, url_resources)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(metric_data)
    }

def test():
    url_resources = retrieve_url_resources()
    urls = []
    for i in url_resources['urls']:
        urls.append(i['url'])
    metric_data = monitor_pages(urls)

    print(metric_data)

test()