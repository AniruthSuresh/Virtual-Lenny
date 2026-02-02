import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['CONNECTIONS_TABLE'])

def lambda_handler(event, context):
    """
    Handle WebSocket disconnection.
    Remove connection ID from DynamoDB.
    """
    connection_id = event['requestContext']['connectionId']
    
    try:
        table.delete_item(Key={'connectionId': connection_id})
        
        print(f"Connection closed: {connection_id}")
        
        return {
            'statusCode': 200,
            'body': 'Disconnected'
        }
        
    except Exception as e:
        print(f" Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': 'Failed to disconnect'
        }