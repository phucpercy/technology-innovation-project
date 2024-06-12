from WebMeasurer.webpage import WebPage

import boto3
import json


def get_urls_from_json(file_name):
    with open(file_name, 'r') as fr:
        data = json.load(fr)
    urls = [e['url'] for e in data['urls']]
    return urls


def monitor_pages(urls):
    data = []

    for url in urls:
        page = WebPage(url)
        page.download_page()
        print(f'{url}\tavailability={page.availability}\tsize={format(page.page_size, "_")}\telapsed={page.time_elapsed:0.2f}secs')

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


def lambda_handler(event, context):
    urls = get_urls_from_json('urls.json')
    metric_data = monitor_pages(urls)
    push_metrics(metric_data)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(metric_data)
    }
