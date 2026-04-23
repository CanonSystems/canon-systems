resource "aws_s3_bucket" "synthesis_vault" {
  bucket                = "${var.name_prefix}-synthesis-vault"
  object_lock_enabled   = false
  force_destroy         = false
}

resource "aws_s3_bucket_versioning" "synthesis_vault" {
  bucket = aws_s3_bucket.synthesis_vault.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "synthesis_vault" {
  bucket = aws_s3_bucket.synthesis_vault.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "synthesis_vault" {
  bucket                  = aws_s3_bucket.synthesis_vault.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_iam_policy_document" "synthesis_vault" {
  statement {
    sid    = "PublisherAccess"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [var.publisher_role_arn]
    }
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
    ]
    resources = ["${aws_s3_bucket.synthesis_vault.arn}/*"]
  }

  statement {
    sid    = "PublisherList"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [var.publisher_role_arn]
    }
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.synthesis_vault.arn]
  }

  dynamic "statement" {
    for_each = var.vault_web_reader_role_arn == null ? [] : [1]
    content {
      sid    = "ReaderRead"
      effect = "Allow"
      principals {
        type        = "AWS"
        identifiers = [var.vault_web_reader_role_arn]
      }
      actions   = ["s3:GetObject", "s3:ListBucket"]
      resources = [aws_s3_bucket.synthesis_vault.arn, "${aws_s3_bucket.synthesis_vault.arn}/*"]
    }
  }
}

resource "aws_s3_bucket_policy" "synthesis_vault" {
  bucket = aws_s3_bucket.synthesis_vault.id
  policy = data.aws_iam_policy_document.synthesis_vault.json
}
