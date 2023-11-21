output "id" {
  value       = aws_instance.anthmec2.*.id
  description = "The instance ID."
}

output "arn" {
  value       = aws_instance.anthmec2.*.arn
  description = "The ARN of the instance."
}

output "availability_zone" {
  value       = aws_instance.anthmec2.*.availability_zone
  description = "The availability zone of the instance."
}

output "placement_group" {
  value       = aws_instance.anthmec2.*.placement_group
  description = "The placement group of the instance."
}

output "public_dns" {
  value       = aws_instance.anthmec2.*.public_dns
  description = "The public DNS name assigned to the instance. For EC2-VPC, this is only available if you've enabled DNS hostnames for your VPC"
}

output "ipv6_addresses" {
  value       = aws_instance.anthmec2.*.ipv6_addresses
  description = "A list of assigned IPv6 addresses, if any"
}

output "primary_network_interface_id" {
  value       = aws_instance.anthmec2.*.primary_network_interface_id
  description = "The ID of the instance's primary network interface."
}

output "private_dns" {
  value       = aws_instance.anthmec2.*.private_dns
  description = "The private DNS name assigned to the instance. Can only be used inside the Amazon EC2, and only available if you've enabled DNS hostnames for your VPC"
}

output "private_ip" {
  value       = aws_instance.anthmec2.*.private_ip
  description = "The private IP address assigned to the instance"
}

output "security_groups" {
  value       = aws_instance.anthmec2.*.security_groups
  description = "The associated security groups."
}

output "vpc_security_group_ids" {
  value       = aws_instance.anthmec2.*.vpc_security_group_ids
  description = "The associated security groups in non-default VPC"
}

output "subnet_id" {
  value       = aws_instance.anthmec2.*.subnet_id
  description = "The VPC subnet ID."
}

output "credit_specification" {
  value       = aws_instance.anthmec2.*.credit_specification
  description = "Credit specification of instance."
}

output "instance_state" {
  value       = aws_instance.anthmec2.*.instance_state
  description = "The state of the instance. One of: pending, running, shutting-down, terminated, stopping, stopped. See Instance Lifecycle for more information."
}

output "user_data" {
  description = "User data executed by the instance"
  value       = aws_instance.anthmec2.*.user_data
}

output "tags" {
  description = "Tags attatched to the instance"
  value       = aws_instance.anthmec2.*.tags
}

output "capacity_reservation_specification" {
  description = "Tags attatched to the instance"
  value       = aws_instance.anthmec2.*.capacity_reservation_specification 
}