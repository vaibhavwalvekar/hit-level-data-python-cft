import json
import logging
import os
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

#boto clients for aws services
sqs_client = boto3.client('sqs')

#environment variables in lambda passed from CFT
queue_url = os.environ['SQSURL']
snstopicarn = os.environ['SNSTopicArn']

def lambda_handler(event, context):
    """
    This acts as the main driver function, publishing messages to SQS and sending notification.
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
        logger.info ('Calling to publish message to SQS')
        MessageId = sqs_publish_msg(bucket_name, file_name)
        logger.info ('Message id of SQS is ' +str(MessageId))
        send_sns_update(MessageId)
        return {
            'statusCode': 200,
            'body': json.dumps('Successfully published sqs message.')
        }
    except Exception as e:
        logger.error ('Failed! Publish SQS Lambda handler has issue ' + str(e))


def sqs_publish_msg(bucket_name, file_name):
    """
    Creates sqs msg dict of the bucket and filename to give information
    to consumer about the data for next process
    Arguments:
        bucket_name: string
        file_name: string
    Returns:
        MessageId: string
    """
    message_attributes = {
        'bucket_name': {
            'DataType': 'String',
            'StringValue': bucket_name
        },
        'file_name': {
            'DataType': 'String',
            'StringValue':  file_name
        }
    }
    message_body = 'The hit file has been DQed, split and published to s3 bucket. '
    try:
        logger.info ('Sending msg')
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body,
            MessageAttributes=message_attributes
        )
        return response['MessageId']
    except Exception as e:
        logger.error("Send sqs message failed " + str(e))


def send_sns_update(msgid):
    """
    Sends an sns notification updating about SQS msg delivered.
    Arguments:
        msg: string
    """
    try:
        sns_client = boto3.client('sns')
        msg = 'A task is waiting in queue to be run, the sqs msg id is ' + str(msgid)
        response = sns_client.publish (
          TargetArn = snstopicarn,
          Message = msg
       )
        logger.info ('SNS notification sent regarding task waiting in sqs')
    except Exception as e:
        logger.error ('Failed! Send sns update has issue ' + str(e))
