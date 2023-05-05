import boto3
import json

snsclient = boto3.client("sns")
 
def lambda_handler(event, context):
    """Receive Slack HTTP POST request and store in SNS for asynchronous parsing"""
    snsclient.publish(
        TopicArn="arn:aws:sns:us-east-2:239219530488:slack", # SNS ARN
        Message=json.dumps({"default": json.dumps(event)}),
        MessageStructure='json'
    )
 
    # This is the acknowledgement (No Content) that needs to be sent within 3 sec
    return {"statusCode": 204}