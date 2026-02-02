import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['CONNECTIONS_TABLE'])

def lambda_handler(event, context):
    """
    Handle new WebSocket connection.
    Store connection ID in DynamoDB for tracking.
    """
    connection_id = event['requestContext']['connectionId']
    
    try:
        table.put_item(Item={
            'connectionId': connection_id,
            'timestamp': str(context.request_id)
        })
        
        print(f" Connection established: {connection_id}")
        
        return {
            'statusCode': 200,
            'body': 'Connected'
        }
        
    except Exception as e:
        print(f" Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': 'Failed to connect'
        }