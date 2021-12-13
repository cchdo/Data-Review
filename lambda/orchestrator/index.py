import json
from logging import exception
import boto3
import base64
import os
import io
import time

lambdaClient = boto3.client('lambda')
s3 = boto3.resource('s3')
ddb = boto3.resource('dynamodb')
failure_table = ddb.Table(os.environ['FAILURE_TABLE'])


def handler(event, context):
    print('request: {}'.format(json.dumps(event)))

    BUCKET_NAME = os.environ['S3_BUCKET_NAME']
    BOTTLE_HANDLER = os.environ['BOTTLE_HANDLER_FUNC_NAME']
    CTD_HANDLER = os.environ['CTD_HANDLER_FUNC_NAME']


    bucket = s3.Bucket(BUCKET_NAME)
    for obj in bucket.objects.all():
        if obj.key.endswith('.csv'):
            lambdaClient.invoke(FunctionName=BOTTLE_HANDLER, InvocationType='Event', Payload=json.dumps({'key': obj.key}))
        elif obj.key.endswith('.zip'):
            lambdaClient.invoke(FunctionName=CTD_HANDLER, InvocationType='Event', Payload=json.dumps({'key': obj.key}))
        else:
            item = {'filename': obj.key, 'failure_type': 'Unhandled file type'}
            failure_table.put_item(Item=item)