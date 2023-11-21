variable "instance_name" {
  description = "(Required) The key name to use for the instance"
  type        = string
}

variable "ebs_block_device" {
  description = "(Optional) \"Default : null\". To add EBS Volume to EC2 instances"
  type        = any
  default     = null
}

variable "disable_api_termination" {
  description = "(Optional) \"Default : true\". If true, enables EC2 Instance Termination Protection."
  default     = true
  type        = bool
}

variable "instance_type" {
  description = "(Optional) \"Default : \"t2.medium\" \". The AWS EC2 tier to use for the DB instances"
  type        = string
  default     = "t2.medium"
}

variable "vpc_security_group_ids" {
  description = "(Required) List of security group names."
  type        = list(string)
}

variable "instance_ami" {
  description = "(Required) The AMI (Amazon Machine Image) that identifies the instance"
  type        = string
}

variable "iam_instance_profile" {
  description = "(Optional) \"Default : \"\" \". The IAM role to assign to the instance"
  type        = string
  default     = ""
}

variable "monitoring" {
  description = "(Optional) \"Default : true\". If true, the launched EC2 instance will have detailed monitoring enabled"
  type        = bool
  default     = true
}

variable "instance_initiated_shutdown_behavior" {
  description = "(Optional) \"Default : \"stop\" .Shutdown behavior for the instance" # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/terminating-instances.html#Using_ChangingInstanceInitiatedShutdownBehavior
  type        = string
  default     = "stop"
}

variable "subnet_ids" {
  description = "(Optional) \"Default : null\". VPC Subnet IDs to launch in"
  type        = list(string)
  default     = null
}

variable "root_volume_size" {
  type        = string
  description = "(Optional) \"Default : \"30\" . AWS EC2 root volume size"
  default     = "30"
}

variable "root_volume_type" {
  type        = string
  description = "(Optional) \"Default : null\". Type of volume. Valid values include standard, gp2, gp3, io1, io2, sc1, or st1. Defaults to gp2."
  default     = null
}

variable "root_volume_iops" {
  type        = string
  description = "(Optional) \"Default : null\". Amount of provisioned IOPS. Only valid for volume_type of io1, io2 or gp3."
  default     = null
}

variable "tags" {
  description = "(Required) A mapping of tags to assign to all resources."
  type        = map(string)
}

variable "delete_on_termination" {
  description = "(Optional) \"Default : true\". Whether the volume should be destroyed on instance termination."
  type        = bool
  default     = true
}

variable "source_dest_check" {
  description = "(Optional) \"Default : true\". Controls if traffic is routed to the instance when the destination address does not match the instance"
  type        = string
  default     = true
}

variable "tenancy" {
  description = "(Optional) \"Default : \"default\" .The tenancy of the instance (if the instance is running in a VPC). Available values: default, dedicated, host."
  type        = string
  default     = "default"
}

variable "kms_key_id" {
  type        = string
  description = "(Required) Amazon Resource Name (ARN) of the KMS Key to use when encrypting the volume."
}

variable "user_data" {
  description = "(Optional) \"Default : \"\" .User data content to attach to the instance"
  type        = string
  default     = ""
}

variable "network_interface_id" {
  type        = list(string)
  description = "(Optional) \"Default : []\". Required when User need to create multiple EC2 instances with Netowkr Interface.list of ID's of the network interface to attach."
  default     = []
}

variable "number_of_instances" {
  type        = number
  description = "(Required) number of instances"
}

variable "network_card_index" {
  type        = number
  description = "(Optional) \"Default : 0\". Integer index of the network card.The default index is 0"
  default = 0
}

variable "delete_on_termination_eni" {
  type        = bool
  description = "(Optional) \"Default : false\". Whether or not to delete the network interface on instance termination. Defaults to false. Currently, the only valid value is false, as this is only supported when creating new network interfaces when launching an instance."
  default     = false
}

variable "host_id" {
  description = "(Optional) \"Default : null\". ID of a dedicated host that the instance will be assigned to. Use when an instance is to be launched on a specific dedicated host."
  type        = string
  default     = null
}

variable "ebs_optimized" {
  description = "(Optional) \"Default : false\". If true, the launched EC2 instance will be EBS-optimized. Note that if this is not set on an instance type that is optimized by default then this will show as disabled but if the instance type is optimized by default then there is no need to set this and there is no effect to disabling it."
  type        = bool
  default     = false
}

variable "hibernation" {
  description = "(Optional) \"Default : false\". If true, the launched EC2 instance will support hibernation."
  type        = bool
  default     = false
}

variable "ephemeral_block_device" {
  description = "(Optional) \"Default : []\". To customize Ephemeral (also known as Instance Store) volumes on the instance."
  type        = any
  default     = []
}

variable "enclave_enabled" {
  description = "(Optional) \"Default : false\". Enable Nitro Enclaves on launched instances."
   type        = bool
  default     = false
}

variable "auto_recovery" {
  description = "(Optional) \"Default : \"disabled\" \". The automatic recovery behavior of the Instance. Can be default or disabled"
  type        = string
  default     = "disabled"
}

variable "capacity_reservation_target" {
  description = "(Optional) \"Default : []\". Indicates the target Capacity Reservation."
  type        = any
  default     = []
}

variable "capacity_reservation_specification" {
  description = "(Optional) \"Default : []\". Indicates the target Capacity Reservation."
  type        = any
  default     = []
}

variable "cpu_credits" {
  description = "(Optional) \"Default : null\". Credit option for CPU usage. Valid values include standard or unlimited.T3 instances are launched as unlimited by default.T2 instances are launched as standard by default."
  type        = string
  default     = null
}

variable "throughput" {
  description = "(Optional) \"Default : null\". Throughput to provision for a volume in mebibytes per second (MiB/s).This is only valid for volume_type of gp3."
  type        = string
  default     = null
}

variable "http_tokens" {
  description = "(Optional) \"Default : required\". Whether or not the metadata service requires session tokens, also referred to as Instance Metadata Service Version 2 (IMDSv2). Valid values include optional or required. Defaults to required."
  type        = string
  default     = "required"
}