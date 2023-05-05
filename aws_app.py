from urllib import parse as urlparse
import base64
import json
import requests

from app import command_handler

def send_to_slack(json, url):
    """Send JSON to Slack response URL"""
    requests.post(url, json=json, timeout=10)

def lambda_handler(event, _):
    """Handle SNS message, retrieve Slack message then run ranking logic"""
    sns_message = json.loads(event['Records'][0]['Sns']['Message'])
    slack_request = dict(urlparse.parse_qsl(base64.b64decode(str(sns_message['body'])).decode('ascii'))) 

    # Build arguments for command_handler
    body = {"text": (slack_request["command"] + " " + slack_request.get("text", "")).strip()}
        
    def ack(text):
        """Send private text to user"""
        respond({"text":text})
        
    def respond(json):
        """Send JSON back to Slack, which may publish in the channel"""
        send_to_slack(json, slack_request["response_url"])
    
    # Call command handler
    return command_handler(ack, body, respond)