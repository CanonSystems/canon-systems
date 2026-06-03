#!/usr/bin/env bash
set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"
PROFILE="${AWS_PROFILE:-canon-systems-v2}"
PREFIX="${PREFIX:-canon-systems-v2-dev}"
CLUSTER="${PREFIX}-cluster"
SERVICE="${PREFIX}-baseline"
TASK_FAMILY="${PREFIX}-knowledge-api"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ECR_URI="222274634742.dkr.ecr.us-east-1.amazonaws.com/${PREFIX}/canon/knowledge-api"
GIT_SHA="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo local)"
TAG="git-${GIT_SHA}-amd64-state-tasks"
ARTIFACT_BUCKET="${PREFIX}-artifacts-4952f257"
TASK_ROLE_NAME="${TASK_ROLE_NAME:-canon-systems-v2-dev-ecs-task-20260413191631346000000002}"
export AWS_PROFILE="$PROFILE"

echo "==> IAM DynamoDB on ${TASK_ROLE_NAME}"
aws iam put-role-policy --role-name "$TASK_ROLE_NAME" --policy-name "canon-state-plane-dynamodb" --policy-document "$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["dynamodb:GetItem","dynamodb:PutItem","dynamodb:UpdateItem","dynamodb:Query","dynamodb:DeleteItem","dynamodb:ConditionCheckItem"],
    "Resource": [
      "arn:aws:dynamodb:${REGION}:222274634742:table/${PREFIX}-canon-state",
      "arn:aws:dynamodb:${REGION}:222274634742:table/${PREFIX}-canon-state/index/*",
      "arn:aws:dynamodb:${REGION}:222274634742:table/${PREFIX}-canon-run-ledger",
      "arn:aws:dynamodb:${REGION}:222274634742:table/${PREFIX}-canon-run-ledger/index/*",
      "arn:aws:dynamodb:${REGION}:222274634742:table/${PREFIX}-canon-tasks",
      "arn:aws:dynamodb:${REGION}:222274634742:table/${PREFIX}-canon-tasks/index/*"
    ]
  }]
}
EOF
)"

echo "==> Docker build+push ${ECR_URI}:${TAG}"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "222274634742.dkr.ecr.${REGION}.amazonaws.com"
docker buildx build --platform linux/amd64 -f "$REPO_ROOT/docker/knowledge-api/Dockerfile" -t "${ECR_URI}:${TAG}" --push "$REPO_ROOT"

echo "==> Register task definition + update service"
CURRENT_JSON="$(aws ecs describe-task-definition --task-definition "$TASK_FAMILY" --region "$REGION" --query 'taskDefinition' --output json)"
NEW_ARN="$(echo "$CURRENT_JSON" | python3 -c "
import json,sys,os
prefix=os.environ['PREFIX']
region=os.environ['REGION']
tag=os.environ['TAG']
ecr=os.environ['ECR_URI']
bucket=os.environ['ARTIFACT_BUCKET']
d=json.load(sys.stdin)
for k in list(d.keys()):
    if k in ('taskDefinitionArn','revision','status','requiresAttributes','compatibilities','registeredAt','registeredBy','deregisteredAt'):
        d.pop(k,None)
c=d['containerDefinitions'][0]
c['image']=f'{ecr}:{tag}'
env={e['name']:e for e in c.get('environment',[])}
def se(n,v): env[n]={'name':n,'value':v}
se('STATE_TABLE_NAME',f'{prefix}-canon-state')
se('STATE_RUN_LEDGER_TABLE_NAME',f'{prefix}-canon-run-ledger')
se('STATE_TASKS_TABLE_NAME',f'{prefix}-canon-tasks')
se('STATE_ARTIFACT_BUCKET',bucket)
se('STATE_ARCHIVE_KEY_PREFIX','canon/packets')
se('AWS_REGION',region)
c['environment']=list(env.values())
print(json.dumps(d))
" | aws ecs register-task-definition --region "$REGION" --cli-input-json file:///dev/stdin --query 'taskDefinition.taskDefinitionArn' --output text)"
export PREFIX REGION TAG ECR_URI ARTIFACT_BUCKET
aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" --task-definition "$NEW_ARN" --force-new-deployment --region "$REGION" --query 'service.{service:serviceName,taskDef:taskDefinition}' --output json
echo "deployed: $NEW_ARN"
