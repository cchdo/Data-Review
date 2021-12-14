import json
from logging import exception
import boto3
import base64
import os
import io
import time
import pandas as pd
import numpy as np
import zipfile

lambdaClient = boto3.client('lambda')
s3 = boto3.client('s3')
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
def handle_zip(byte_data):
    dfs = []
    with zipfile.ZipFile(byte_data) as zip:
        for subfile in zip.namelist():
            if subfile.endswith('.csv'):
                with zip.open(subfile) as f:

                    title = f.readline()
                    lines = f.readlines()

                    #Each line is read as bytes in the Zipfile package, so here we convert to strings
                    lines = [line.decode('iso-8859-1') for line in lines]

                    #Discard all the header lines that start with '#'
                    without_header = [line for line in lines if line[0] != '#']
                    without_header = [line for line in without_header if '=' not in line]
                    
                    #Pop rows that would cause NaN values, so pandas doesn't convert columns to floats
                    units = without_header.pop(1)
                    end_string = without_header.pop(-1)

                    #Read remaining lines as a csv, get column names and save results
                    df = pd.read_csv(io.StringIO(''.join(without_header)))
                    
                    #CHANGE THIS TO RETURN FULL DATAFRAME
                    dfs.append(df)
                    
                    dfs.append(get_missingness(df))
        #zip_cols.append(cols_in_subfile)
    return dfs

def handler(event, context):
    print('request: {}'.format(json.dumps(event)))

    BUCKET_NAME = os.environ['S3_BUCKET_NAME']
    key = event['key']
    try:
        #Get file from bucket
        print("Downloading File")
        fname = '/tmp/' + key
        s3.download_file(BUCKET_NAME, key, '/tmp/' + key)
        print("File Downloaded")

        #Parse file
        with open(fname, 'rb') as f:
            dfs = handle_zip(f)
        print("File Parsed")

        #Write aggregate values to db
        total_observations = sum([len(df) for df in dfs]))]
        item = {
            'filename': key,
            'observations': total_observations
        }
        print("Writing to DB")
        output_table.put_item(Item=item)
    except Exception as e:
        print(e)
        item = {
            'filename': key,
            'function': FUNC_NAME,
            'logGroup': LOG_GROUP,
            'logStream': LOG_STREAM,
        }
        failure_table.put_item(Item=item)