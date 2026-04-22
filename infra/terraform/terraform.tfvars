# Non-secret defaults for the deployed canon-systems-v2 dev stack (us-east-1).
# Adjust if you create additional environments.

aws_region   = "us-east-1"
project_name = "canon-systems-v2"
environment  = "dev"

ecr_repository_names = [
  "canon/jira-bridge",
  "canon/knowledge-api",
  "canon/knowledge-worker",
  "canon/temporal-runtime",
]

# Baseline ECS task count (was 1 in state before; root module default is 0).
ecs_desired_count = 1
