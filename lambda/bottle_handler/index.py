import json
from logging import exception
import boto3
import base64
import os
import io
import time
import numpy as np
import pandas as pd

lambdaClient = boto3.client('lambda')
s3 = boto3.resource('s3')
ddb = boto3.resource('dynamodb')
failure_table = ddb.Table(os.environ['FAILURE_TABLE'])
output_table = ddb.Table(os.environ['RESULTS_TABLE'])

FUNC_NAME = os.environ['AWS_LAMBDA_FUNCTION_NAME']
LOG_GROUP = os.environ['AWS_LAMBDA_LOG_GROUP_NAME']
LOG_STREAM = os.environ['AWS_LAMBDA_LOG_STREAM_NAME']

def get_missingness(df):
    
    #Replace -999 values with nan
    df = df.replace('.*-999.00', np.nan, regex=True)
    df = df.replace(-999.00, np.nan)
    df = df.replace(-999, np.nan)
    
    missingness_rates = df.isna().sum()
    missingness_rates['df_len'] = len(df)
    
    return missingness_rates

def handle_csv(byte_data):
    """
    Takes in raw byte data that represents an exchange csv

    Returns the csv as a pandas DataFrame, stripped of its headers
    """
    #Convert data into list of strings
    lines = byte_data.decode('iso-8859-1').splitlines()

    title = lines.pop(0)

    #Discard all the header lines that start with '#'
    without_header = [line for line in lines if line[0] != '#']

    #Pop rows that would cause NaN values, so pandas doesn't convert columns to floats
    units = without_header.pop(1)
    end_string = without_header.pop(-1)
    
    #Read remaining lines as a csv, get column names and save results
    df = pd.read_csv(io.StringIO('\n'.join(without_header)))

    #RETURN HERE TO RETURN FULL DATAFRAME
    #return df

    #Get missingness rates
    missingness_rates = get_missingness(df)
    return missingness_rates

def handler(event, context):
    print('request: {}'.format(json.dumps(event)))

    BUCKET_NAME = os.environ['S3_BUCKET_NAME']
    key = event['Records'][0]['s3']['object']['key']
    try:
        #Get file from bucket
        fname = '/tmp/' + key
        s3.download_file(BUCKET_NAME, key, '/tmp/' + key)

        #Parse file
        with open(fname, 'rb') as f:
            df = handle_csv(f)
        
        #Write aggregate values to db
        print(df)
    except:
        item = {
            'filename': key,
            'function': FUNC_NAME,
            'logGroup': LOG_GROUP,
            'logStream': LOG_STREAM,
        }
        failure_table.put_item(Item=item)