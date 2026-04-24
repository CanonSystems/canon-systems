data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

resource "random_password" "db" {
  count   = var.db_password == null ? 1 : 0
  length  = 32
  special = false
}

locals {
  db_password_effective = var.db_password != null ? var.db_password : random_password.db[0].result
}

module "vpc" {
  source = "./modules/vpc"

  name_prefix        = "${var.project_name}-${var.environment}"
  vpc_cidr           = var.vpc_cidr
  availability_zones = local.azs
  single_nat_gateway = var.single_nat_gateway
}

module "ecr" {
  source = "./modules/ecr"

  name_prefix          = "${var.project_name}-${var.environment}"
  repository_names     = var.ecr_repository_names
  image_tag_mutability = "MUTABLE"
}

module "artifacts_bucket" {
  source = "./modules/s3-artifacts"

  name_prefix = "${var.project_name}-${var.environment}"
}

module "placeholders" {
  source = "./modules/secrets"

  name_prefix = "${var.project_name}-${var.environment}"
  secret_names = concat(
    var.placeholder_secret_names,
    var.memory_layer_secret_suffixes,
  )
}

module "ecs_baseline" {
  source = "./modules/ecs-fargate"

  name_prefix        = "${var.project_name}-${var.environment}"
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  container_name  = "app"
  container_image = var.ecs_container_image
  container_port  = var.ecs_container_port
  cpu             = var.ecs_cpu
  memory          = var.ecs_memory
  desired_count   = var.ecs_desired_count

  s3_bucket_arn = module.artifacts_bucket.bucket_arn
  secret_arns   = values(module.placeholders.secret_arns)

  ingress_enabled                     = var.ecs_ingress_enabled
  ingress_target_group_arn            = var.ecs_ingress_target_group_arn
  ingress_source_security_group_ids = var.ecs_ingress_source_security_group_ids

  depends_on = [module.placeholders]
}

module "rds" {
  source = "./modules/rds-postgres"

  name_prefix = "${var.project_name}-${var.environment}"

  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  allowed_security_group_ids = [module.ecs_baseline.tasks_security_group_id]

  db_name             = var.db_name
  master_username     = var.db_username
  master_password     = local.db_password_effective
  instance_class      = var.db_instance_class
  allocated_storage   = var.db_allocated_storage
  engine_version      = var.db_engine_version
  skip_final_snapshot = var.rds_skip_final_snapshot
}

module "state_table" {
  source      = "./modules/dynamodb-canon-state"
  name_prefix = "${var.project_name}-${var.environment}"
}

module "axon_snapshots" {
  source      = "./modules/axon-snapshots"
  name_prefix = "${var.project_name}-${var.environment}"
}
