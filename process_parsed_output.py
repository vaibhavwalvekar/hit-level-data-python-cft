import json
import boto3
import logging
import os
import awswrangler as wr
from urllib.parse import urlparse
import re
import numpy as np
import pandas as pd
from datetime import date

logger = logging.getLogger()
logger.setLevel(logging.INFO)

#boto clients for aws services
sqs_client = boto3.client('sqs')
s3_resource = boto3.resource('s3')

#environment variables in lambda passed from CFT
queue_url = os.environ['SQSURL']
final_bucket_name = os.environ['final_bucket']
final_output_file_name = os.environ['final_output_file_name']

def lambda_handler(event, context):
    """
    This acts as the main driver function, processing files to calculate best search keyword and search engine domain based on revenue.
    It accepts events and context as argument from the AWS services calling the lambda function.
    Arguments:
        event: Dict
        context: Dict
    Returns:
        Dict
    """
    try:
        receipt_handle = event['Records'][0]['receiptHandle']
        message_attributes = event['Records'][0]['messageAttributes']
        bucket_name = message_attributes['bucket_name']['stringValue']
        file_path = message_attributes['file_name']['stringValue']
        prefix = file_path.rsplit('/', 1)[0]
        logger.info ('Message has been received.')
        logger.info ('Message was received from bucket name is  ' +bucket_name)
        logger.info ('File prefix  is ' + prefix)
        df = read_files_s3(bucket_name, prefix)
        df = revenue_calc(df)
        write_to_s3(df, prefix)
        delete_sqs_msg(receipt_handle)
        return {
            'statusCode': 200,
            'body': json.dumps('Successfully uploaded final output to s3.')
        }
    except Exception as e:
        logger.error ('Failed! Process parsed output Lambda handler has issue ' + str(e))


def revenue_calc(df):
    """
    This funtion processes the combined dataframe of all the files from s3 to unpack different columns which are then aggregated to caluclate
    revenue per search keyword and search engine domain.
    Arguments:
        df: pandas dataframe
    Returns:
        final_df: pandas dataframe
    """
    try:
        logger.info ('Processing url.')
        df['domain_name'], df['url_query'] = zip(*df.apply(url_parse, axis=1))
        df['search_compound_string'] = [next((l[x] for x in range(len(l)) if 'p=' in l[x] or 'q=' in l[x]), None) for l in df['url_query']]
        df['search_engine_domain'] = df['domain_name'].str.split('.', 1).str[-1]
        df['search_keyword'] = df['search_compound_string'].str.split('=').str[-1]
        df['search_keyword'] = df['search_keyword'].str.replace('+',' ')
        df['search_keyword'] = df['search_keyword'].str.lower()
        df_grouped_sorted = df.sort_values(by=['ip','date_time'], ascending=True)

        output_df = pd.DataFrame(columns = ['search_engine_domain', 'search_keyword', 'revenue'])
        current_domain_name = ''
        current_search_keyword = ''
        for index, row in df_grouped_sorted.iterrows():
            if pd.notnull(row['search_keyword']):
                current_domain_name = row['search_engine_domain']
                current_search_keyword = row['search_keyword']
            total_revenue = row['total_revenue']
            if pd.notnull(row['total_revenue']) and row['event_list'] == 1:
                output_df = output_df.append({'search_engine_domain' : current_domain_name, 'search_keyword' : current_search_keyword, 'revenue' : total_revenue},
                  ignore_index = True)

        final_df = output_df.groupby(['search_engine_domain', 'search_keyword'])['revenue'].sum().sort_values(ascending=[False])
        logger.info ('Final output DF consisting of revenue numbers haas been calculated.')
        return final_df
    except Exception as e:
        logger.error ('Failed!  Revenue calculation has a issue ' + str(e))


def url_parse(row):
    return urlparse(row['referrer']).netloc, urlparse(row['referrer']).query.strip('&').split('&')


def read_files_s3(bucket_name, prefix):
    """
    Read files from s3 and create a pandas dataframe
    Arguments:
        bucket_name: string
        prefix: string
    Returns:
        df: pandas dataframe
    """
    try:
        logger.info ('Reading from bucket.')
        df = wr.s3.read_csv('s3://' + bucket_name +'/' + prefix +'/', sep='\t')
        return df
    except Exception as e:
        logger.error ('Failed! Reading from s3 has issue ' + str(e))

def write_to_s3(df, prefix):
    """
    Write final output file to s3
    Arguments:
        df: dataframe
        prefix: string
    """
    try:
        logger.info ('Writing final output to bucket.')
        today = date.today()
        file_name = str(today) + final_output_file_name
        wr.s3.to_csv(df = df, path = 's3://' + final_bucket_name +'/' + prefix +'/' + file_name, sep='\t')
    except Exception as e:
        logger.error ('Failed! Writing to s3 has issue ' + str(e))


def delete_sqs_msg(receipt_handle):
    """
    Delete message from sqs queue
    Arguments:
        receipt_handle: string
    """
    try:
        logger.info ('Deleting msg from sqs.')
        sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        logger.info ('Message has been deleted.')
    except Exception as e:
        logger.error ('Failed! Delete sqs msg has issue ' + str(e))
