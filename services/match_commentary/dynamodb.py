# backend/shared/dynamodb.py
import boto3
import os
import uuid

dynamodb = boto3.resource("dynamodb")
table_name = os.getenv("DYNAMODB_TABLE", "match_events")
table = dynamodb.Table(table_name)

def store_events_in_dynamodb(events):
    for event in events:
        try:
            table.put_item(Item={
                "event_id": str(uuid.uuid4()),
                "team": event.get("team", {}).get("name", "Unknown"),
                "type": event.get("type", "Unknown"),
                "player": event.get("player", {}).get("name", "Unknown"),
                "minute": str(event.get("time", {}).get("elapsed", 0)),
                "raw": str(event)  # Store raw event as fallback
            })
        except Exception as e:
            print(f"Error saving to DynamoDB: {e}")