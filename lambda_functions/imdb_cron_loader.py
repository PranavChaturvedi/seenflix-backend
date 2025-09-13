import boto3
import os
import datetime


def handler(event, context):
    content_type = event.get('type', 'movie')
    week_pattern = event.get('week_pattern', 'even')
    
    # Calculate current week number (ISO week)
    current_date = datetime.datetime.now()
    current_week = current_date.isocalendar()[1]
    
    # Check if we should run based on week pattern
    should_run = False
    if week_pattern == "even" and current_week % 2 == 0:
        should_run = True
    elif week_pattern == "odd" and current_week % 2 == 1:
        should_run = True
    
    if not should_run:
        print(f"Skipping {content_type} run - wrong week pattern. Current week: {current_week}, Required: {week_pattern}")
        return {"statusCode": 200, "body": "Skipped - wrong week"}

    print(f"Running {content_type} loader - Week {current_week} ({week_pattern})")

    ecs_client = boto3.client("ecs") 
    ecs_client.run_task(
        capacityProviderStrategy=[
            {"capacityProvider": "FARGATE", "base": 0, "weight": 1}
        ],
        cluster="seenflix-load-supabase",
        count=1,
        overrides={
            "containerOverrides": [
                {
                    "name": "load_db",
                    "command": ["python", "load_db.py", "--media", content_type],
                }
            ],
            "taskRoleArn": os.environ["ECS_TASK_EXECUTION_ROLE"],
            "executionRoleArn": os.environ["ECS_TASK_EXECUTION_ROLE"],
        },
        taskDefinition="seenflix_loaddb_supabase",
        networkConfiguration={
            "awsvpcConfiguration": {
                "securityGroups": [os.environ["VPC_SGROUP"]],
                "subnets": [*os.environ["VPC_SUBNETS"].split(",")],
                "assignPublicIp": "ENABLED",
            }
        },
    )
