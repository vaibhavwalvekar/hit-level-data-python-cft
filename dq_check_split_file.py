import json
import boto3
import logging
import os
import numpy as np
from io import StringIO
from datetime import date
import awswrangler as wr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

#boto clients for aws services
try:
    s3_client = boto3.client('s3')
    sns_client = boto3.client('sns')
except Exception as e:
    logger.error ('Failed! Issue in making boto client connections with AWS resources ' + str(e))
    raise e
#environment variables in lambda passed from CFT
try:
    target_bucket = os.environ['target_bucket']
    file_type = os.environ['file_type']
    snstopicarn = os.environ['SNSTopicArn']
    expected_columns = json.loads(os.environ['expected_columns'])
    cols_for_analysis = json.loads(os.environ['cols_for_analysis'])
    product_list_split_cols = json.loads(os.environ['product_list_split_cols'])
except Exception as e:
    logger.error ('Failed! Issue with reading environment variables in DQ Lambda function ' + str(e))
    raise e

def lambda_handler(event, context):
    """
    This acts as the main driver function, calling DQ functions and sending notification based on results.
    It accepts events and context as argument from the AWS services calling the lambda function.
    Arguments:
        event: Dict
        context: Dict
    Returns:
        Dict
    """
    try:
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        file_name = event['Records'][0]['s3']['object']['key']
        response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
        msg = ''
        dq_flag = True
        if check_file_format(response):
            logger.info ('File format looks good.')
            msg += 'File format looks good. '
        else:
            logger.error('File format has issue.')
            msg += 'File format has issue. '
            dq_flag = False

        if check_file_columns(response):
            logger.info('File columns look good.')
            msg += 'File columns look good. '
        else:
            logger.error('File columns has issue.')
            msg += 'File columns has issue. '
            dq_flag = False
        if dq_flag:
            msg = transform_split_files(bucket_name, file_name, msg)
        send_dq_report(msg)
        return {
            'statusCode': 200,
            'body': json.dumps('DQ complete and file split was successful.')
        }
    except Exception as e:
        logger.error ('Failed! DQ Lambda handler has issue ' + str(e))
        raise e


def check_file_format(response):
    """
    Checks file format of the incoming file with expected.
    Arguments:
        response: s3 get object
    Returns:
        Boolean
    """
    try:
        ContentType = response['ResponseMetadata']['HTTPHeaders']['content-type']
        if ContentType == file_type:
            return True
        else:
            return False
    except Exception as e:
        logger.error ('Failed! Issue with checking file format ' + str(e))
        raise e

def check_file_columns(response):
    """
    Checks file columns of the incoming file with expected.
    Arguments:
        response: s3 get object
    Returns:
        Boolean
    """
    try:
        contents = response['Body'].read().decode('UTF-8')
        actual_columns = contents.split('\n')[0].split('\t')
        if len(actual_columns) != len(expected_columns):
            return False
        else:
            for i in expected_columns:
                if i in actual_columns:
                    return True
                else:
                    return False
    except Exception as e:
        logger.error ('Failed! Issue with checking file columns ' + str(e))
        raise e

def send_dq_report(msg):
    """
    Sends an sns notification updating about DQ results.
    Arguments:
        msg: string
    """
    try:
        sns_client.publish (
          TargetArn = snstopicarn,
          Message = msg
       )
        logger.info ('SNS notification has been sent')
    except Exception as e:
        logger.error ('Failed! Issue with sending DQ report ' + str(e))
        raise e

def transform_split_files(bucket_name, file_name, msg):
    """
    Unpacks some of the column as per required for analysis.
    Splits files into smaller files.
    Creates and uploads indicator file for next process.
    Arguments:
        bucket_name: string
        file_name: string
        msg: string
    Returns:
        msg: string
    """
    try:
        target_file_name = file_name.split('.')[0]
        s3_resource = boto3.resource('s3')
        hit_data_df = wr.s3.read_csv(path=['s3://' + bucket_name + '/' + file_name], sep='\t')
        hit_data_df_subset = hit_data_df[cols_for_analysis]
        hit_data_df_subset[product_list_split_cols] = hit_data_df_subset['product_list'].str.split(';', expand=True)
        file_num = 1
        today = date.today()
        for chunk in np.array_split(hit_data_df_subset, 5):
            csv_buffer = StringIO()
            chunk.to_csv(csv_buffer, sep = '\t', index =False)
            s3_resource.Object(target_bucket, str(today) + '/' + target_file_name + '_' + str(file_num) + '.tsv').put(Body=csv_buffer.getvalue())
            file_num +=1
        result_dict = {}
        result_dict['Result'] = 'Success'
        resultfileName = str(today) + '/' + 'Success' + '.json'
        uploadByteStream = bytes(json.dumps(result_dict).encode('UTF-8'))
        s3_client.put_object(Bucket=target_bucket, Key=resultfileName, Body=uploadByteStream)
        msg += '\nSuccess! File has been split in ' + str(file_num - 1) + ' smaller files. Upload is complete.'
        return msg
    except Exception as e:
        logger.error ('Failed! There has been an issue with splitting of file. The error is ' + str(e))
        raise e
