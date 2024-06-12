import json

import boto3
from web_measurer.webpage import WebPage

def retrieve_url_resources():
    s3_client = boto3.client('s3')

    response = s3_client.get_object(Bucket='tip-monitoring-url-resources', Key='urls.json')

    object_content = response['Body'].read().decode('utf-8')
    data = json.loads(object_content)

    return data


def measuring_handler(event, context):
    urls = []
    response = []

    data = retrieve_url_resources()

    for i in data['urls']:
        urls.append(i['url'])

    for url in urls:
        page = WebPage(url)
        page.download_page()
        print(f'{url}\tavailability={page.availability}\tsize={format(page.page_size, "_")}\telapsed={page.time_elapsed:0.2f}secs')
        response.append({
            "url": url,
            "availability": page.availability,
            "page_size": page.page_size,
            "response_time": page.time_elapsed
        })

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "data": response
        })
    }
