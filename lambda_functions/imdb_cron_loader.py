import boto3
import os


def handler(event, context):
    ecs_client = boto3.client("ecs")
    ecs_client.run_task(
        capacityProviderStrategy=[
            {"capacityProvider": "FARGATE", "base": 0, "weight": 1}
        ],
        cluster="seenflix-load-supabase",
        count=1,
        overrides={
            "containerOverrides": [
                {"name": "load_db", "command": ["python", "load_db.py"]}
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
