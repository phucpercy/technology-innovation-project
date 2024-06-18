import json

import boto3
from web_measurer.webpage import WebPage


def retrieve_url_resources():
    s3_client = boto3.client('s3')

    response = s3_client.get_object(Bucket='tip-monitoring-url-resources', Key='urls.json')

    object_content = response['Body'].read().decode('utf-8')
    data = json.loads(object_content)

    return data


def monitor_pages(urls):
    data = []

    for url in urls:
        page = WebPage(url)
        page.download_page()
        print(
            f'{url}\tavailability={page.availability}\tsize={format(page.page_size, "_")}\telapsed={page.time_elapsed:0.2f}secs')

        data.append({
            'url': page.url,
            'availability': 1 if page.availability else 0,
            'page_size': page.page_size,
            'page_time': page.time_elapsed
        })

    return data

def push_metrics(data):
    metric_data = []
    for e in data:
        metric = {
            'MetricName': 'Page Time',
            'Unit': 'Seconds',
            'Dimensions': [
                {
                    'Name': 'URL',
                    'Value': e['url']
                }
            ],
            'Value': e['page_time']
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
    push_metrics(metric_data)

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