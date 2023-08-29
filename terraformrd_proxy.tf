##https://prod.liveshare.vsengsaas.visualstudio.com/join?4DD4FF31E3AD8EA09BF066DD030C319AC64B
resource "aws_db_proxy" "db_proxy" {
  name                   = var.name
  debug_logging          = var.debug_logging == "" ? null : var.debug_logging
  engine_family          = var.engine_family
  idle_client_timeout    = var.idle_client_timeout == "" ? null : var.idle_client_timeout
  require_tls            = var.require_tls == "" ? null : var.require_tls
  role_arn               = var.role_arn
  vpc_security_group_ids = var.vpc_security_group_ids == [] ? null : var.vpc_security_group_ids
  vpc_subnet_ids         = var.vpc_subnet_ids
  tags                   = var.tags

  dynamic "auth" {
    for_each = var.auth
    content {
      auth_scheme = auth.value["auth_scheme"] == "" ? null : auth.value["auth_scheme"]
      description = auth.value["description"] == "" ? null : auth.value["description"]
      iam_auth    = auth.value["iam_auth"] == "" ? null : auth.value["iam_auth"]
      secret_arn  = auth.value["secret_arn"] == "" ? null : auth.value["secret_arn"]
      username    = auth.value["username"] == "" ? null : auth.value["username"]
    }
  }

}

resource "aws_db_proxy_default_target_group" "this" {

  db_proxy_name = aws_db_proxy.db_proxy.name

  dynamic "connection_pool_config" {
    for_each = var.connection_pool_config

    content {
      connection_borrow_timeout    = connection_pool_config.value["connection_borrow_timeout"] == "" ? null : connection_pool_config.value["connection_borrow_timeout"]
      init_query                   = connection_pool_config.value["init_query"] == "" ? null : connection_pool_config.value["init_query"]
      max_connections_percent      = connection_pool_config.value["max_connections_percent"] == "" ? null : connection_pool_config.value["max_connections_percent"]
      max_idle_connections_percent = connection_pool_config.value["max_idle_connections_percent"] == "" ? null : connection_pool_config.value["max_idle_connections_percent"]
      session_pinning_filters      = connection_pool_config.value["session_pinning_filters"] == "" ? null : connection_pool_config.value["session_pinning_filters"]
    }
  }
}

###################### Targets ###############################

resource "aws_db_proxy_target" "db_instance" {
  count  = var.db_instance_identifier ? 0 : 1 

  db_proxy_name          = aws_db_proxy.db_proxy.name
  target_group_name      = aws_db_proxy_default_target_group.this.name
  db_instance_identifier = var.db_instance_identifier[0]
}

resource "aws_db_proxy_target" "db_cluster" {
  count = var.db_cluster_identifier ? 0 : 1

  db_proxy_name         = aws_db_proxy.db_proxy.name
  target_group_name     = aws_db_proxy_default_target_group.this.name
  db_cluster_identifier = var.db_cluster_identifier[0]
}

##################### Cloudwatch Log #######################

resource "aws_cloudwatch_log_group" "this" {

  name              = "/aws/rds/proxy/${var.name}"
  retention_in_days = var.retention_in_days_rds_proxy
  kms_key_id        = var.kms_key_id_log_group
  skip_destroy      = false
  tags = var.tags
}







