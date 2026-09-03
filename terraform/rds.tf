resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-db-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "postgres" {
  identifier                = "${var.project}-postgres"
  engine                    = "postgres"
  engine_version            = "15.8"
  instance_class            = var.db_instance_class
  allocated_storage         = 20
  max_allocated_storage     = 100
  db_name                   = "researchdb"
  username                  = "dbadmin"
  password                  = random_password.db_password.result
  db_subnet_group_name      = aws_db_subnet_group.main.name
  vpc_security_group_ids    = [aws_security_group.rds.id]
  multi_az                  = var.db_multi_az
  deletion_protection       = false
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.project}-postgres-final-snapshot"
  backup_retention_period   = 7
  backup_window             = "03:00-04:00"
  maintenance_window        = "sun:05:00-sun:06:00"
  tags                      = { Name = "${var.project}-postgres" }
}

resource "random_password" "db_password" {
  length  = 24
  special = false
}
