resource "aws_dynamodb_table" "this" {
  name         = "${var.name_prefix}-canon-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  ttl {
    attribute_name = "lease_expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  deletion_protection_enabled = true

  tags = {
    Purpose = "canon-state"
  }
}

resource "aws_dynamodb_table" "run_ledger" {
  name         = "${var.name_prefix}-canon-run-ledger"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  deletion_protection_enabled = true

  tags = {
    Purpose = "canon-run-ledger"
  }
}

# Assignable-task event plane for `canon task` (server-authoritative tasks).
# Append-only event rows keyed pk = "{company_id}#tasks", sk = "{task_ref}#evt#{event_id}".
resource "aws_dynamodb_table" "tasks" {
  name         = "${var.name_prefix}-canon-tasks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  deletion_protection_enabled = true

  tags = {
    Purpose = "canon-tasks"
  }
}
