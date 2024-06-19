import json
# import os
# import boto3
# import csv
# import concurrent.futures
# from datetime import datetime

# s3_client = boto3.client("s3")
# dynamodb_client = boto3.client("dynamodb")
#
# table_name = os.getenv("TABLE_NAME")
# bucket_name = os.getenv("ASSET_BUCKET_NAME")
# object_key = os.getenv("OBJECT_KEY")
#
#
# def download_csv_from_s3():
#     response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
#     content = response["Body"].read().decode("utf-8")
#     return content
#
#
# def extract_urls_from_csv(file_content):
#     urls = []
#
#     csv_lines = file_content.strip().splitlines()
#     csv_reader = csv.reader(csv_lines, delimiter=',')
#
#     next(csv_reader, None)
#
#     for row in csv_reader:
#         if len(row) >= 2:
#             urls.append(row[1])
#
#     return urls
#
#
# def check_url_status(urls):
#     status_results = []
#     current_timestamp = str(datetime.now())
#
#     def check_single_url(url):
#         try:
#             start_time = datetime.now()
#             response = requests.get(url, verify=False, timeout=5)
#             end_time = datetime.now()
#
#             response_time = (end_time - start_time).total_seconds()
#             page_size = len(response.content)
#             availability = 1 if response.status_code == 200 else 0
#             page_time = response.headers.get('date')
#
#             status_results.append({
#                 "url": url,
#                 "response_time": response_time,
#                 "availability": availability,
#                 "page_size": page_size,
#                 "page_time": page_time
#             })
#         except requests.exceptions.Timeout:
#             status_results.append({
#                 "url": url,
#                 "response_time": None,
#                 "availability": 0,
#                 "page_size": None,
#                 "page_time": None
#             })
#         except:
#             status_results.append({
#                 "url": url,
#                 "response_time": None,
#                 "availability": 0,
#                 "page_size": None,
#                 "page_time": None
#             })
#
#     with concurrent.futures.ThreadPoolExecutor() as executor:
#         executor.map(check_single_url, urls)
#
#     return status_results
#
#
# def batch_put_items_to_dynamodb(items):
#     put_requests = [
#         {
#             "PutRequest": {
#                 "Item": {
#                     "url": {"S": item["url"]},
#                     "response_time": {'N': str(item['response_time'])} if item['response_time'] is not None else {'NULL': True},
#                     "availability": {'N': str(item['availability'])},
#                     "page_size": {'N': str(item['page_size'])} if item['page_size'] is not None else {'NULL': True},
#                     "page_time": {'S': item['page_time']} if item['page_time'] is not None else {'NULL': True},
#                 }
#             }
#         }
#         for item in items
#     ]
#
#     response = dynamodb_client.batch_write_item(RequestItems={table_name: put_requests})
#
#     return response
#
#
def lambda_handler(event, context):
    # csv_content = download_csv_from_s3()
    # urls = extract_urls_from_csv(file_content=csv_content)
    # status_results = check_url_status(urls)
    #
    # batch_put_items_to_dynamodb(status_results)
    s1 = json.dumps(event)
    inv_event = json.loads(s1)
    print(inv_event)
    response = {
        'message': 'success'
    }
    return response
