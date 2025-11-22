# =============================================================================
# DynamoDB Table for Music Video Projects
# =============================================================================

resource "aws_dynamodb_table" "mv_projects" {
  name           = "${var.environment}-MVProjects"
  billing_mode   = "PAY_PER_REQUEST"  # On-demand billing for cost optimization
  hash_key       = "PK"
  range_key      = "SK"

  # Partition and Sort Keys
  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # GSI attributes
  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  # Global Secondary Index for status queries
  global_secondary_index {
    name            = "status-created-index"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = var.dynamodb_enable_pitr
  }

  # Enable encryption at rest
  server_side_encryption {
    enabled = var.dynamodb_enable_encryption
  }

  # TTL attribute (optional, for future use)
  ttl {
    attribute_name = "ttl"
    enabled        = false
  }

  tags = {
    Name        = "${var.environment}-MVProjects"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "bad-apples-mvp"
  }
}

# CloudWatch Alarms for DynamoDB
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttled_requests" {
  alarm_name          = "${var.environment}-MVProjects-throttled-requests"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "UserErrors"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert when DynamoDB has too many throttled requests"

  dimensions = {
    TableName = aws_dynamodb_table.mv_projects.name
  }

  tags = {
    Name        = "${var.environment}-DynamoDB-Throttling-Alarm"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
