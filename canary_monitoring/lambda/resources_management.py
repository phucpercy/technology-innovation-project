import datetime
import json
import uuid

import boto3
import os

from boto3.dynamodb.conditions import Key

dynamodb_table_name = os.environ["DYNAMO_RESOURCES_TABLE_NAME"]
client = boto3.client('dynamodb')
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(dynamodb_table_name)

def get_item_by_id(id):
    resp = table.query(
        KeyConditionExpression=Key('id').eq(id)
    )
    return resp["Items"][0]


def lambda_handler(event, context):
    print(event)
    body = {}
    statusCode = 200
    headers = {
        "Content-Type": "application/json"
    }

    try:
        if event['routeKey'] == "DELETE /resources/{id}":
            item = get_item_by_id(event['pathParameters']['id'])
            table.delete_item(
                Key={
                    'id': item['id'],
                    'timestamp': item['timestamp']
                }
            )
            body = 'Deleted item ' + event['pathParameters']['id']
        elif event['routeKey'] == "GET /resources/{id}":
            body = get_item_by_id(event['pathParameters']['id'])
        elif event['routeKey'] == "GET /resources":
            body = table.scan()
            body = body["Items"]
            responseBody = []
            for items in body:
                responseBody.append(items)
            body = responseBody
        elif event['routeKey'] == "PUT /resources":
            requestJSON = json.loads(event['body'])
            item = {
                    'id': str(uuid.uuid4()),
                    'timestamp': datetime.datetime.now().isoformat(),
                    'urls': requestJSON['urls']
                }
            table.put_item(
                Item=item
            )
            body = item
    except KeyError:
        statusCode = 400
        body = 'Unsupported route: ' + event['routeKey']
    body = json.dumps(body)
    res = {
        "statusCode": statusCode,
        "headers": headers,
        "body": body
    }
    return res