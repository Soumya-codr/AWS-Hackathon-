// =============================================================================
// CloudSentinel Zero-Trust AWS Cedar Policy Definitions
// Enforces strict fail-closed constraints on AI-generated Infrastructure-as-Code.
// =============================================================================

// Default Baseline Permit: Only compliant resources with no forbid triggers pass
@id("default-permit")
permit(principal, action, resource);

// -----------------------------------------------------------------------------
// RULE 1: IAM Least Privilege & Zero Wildcard Administration
// Forbids AdministratorAccess or wildcard actions ("*") paired with wildcard resources.
// -----------------------------------------------------------------------------
@id("no-admin-access")
forbid(principal, action, resource)
when {
    (resource.type == "AWS::IAM::Role" || resource.type == "AWS::IAM::Policy" || resource.type == "aws_iam_role" || resource.type == "aws_iam_policy") &&
    (resource.has_admin_access == true || resource.has_wildcard_policy == true)
};

// -----------------------------------------------------------------------------
// RULE 2: S3 Data Protection & Public Access Block
// Forbids any S3 bucket that has public exposure, lacks public access block, or allows public ACLs.
// -----------------------------------------------------------------------------
@id("no-public-s3")
forbid(principal, action, resource)
when {
    (resource.type == "AWS::S3::Bucket" || resource.type == "aws_s3_bucket") &&
    (resource.is_public == true || resource.public_access_block == false)
};

// -----------------------------------------------------------------------------
// RULE 3: S3 Mandatory At-Rest Encryption
// Forbids S3 buckets without server-side encryption enabled (KMS / AES256).
// -----------------------------------------------------------------------------
@id("no-unencrypted-s3")
forbid(principal, action, resource)
when {
    (resource.type == "AWS::S3::Bucket" || resource.type == "aws_s3_bucket") &&
    resource.encryption_enabled == false
};

// -----------------------------------------------------------------------------
// RULE 4: Zero Open Ingress (0.0.0.0/0)
// Forbids any Security Group rule granting unbounded 0.0.0.0/0 ingress to sensitive or all ports.
// -----------------------------------------------------------------------------
@id("no-wildcard-ingress")
forbid(principal, action, resource)
when {
    (resource.type == "AWS::EC2::SecurityGroup" || resource.type == "aws_security_group") &&
    resource.has_wildcard_ingress == true
};

// -----------------------------------------------------------------------------
// RULE 5: Storage & Database Encryption
// Forbids unencrypted RDS DB instances, EBS volumes, and DynamoDB tables.
// -----------------------------------------------------------------------------
@id("no-unencrypted-database")
forbid(principal, action, resource)
when {
    (resource.type == "AWS::RDS::DBInstance" || resource.type == "AWS::DynamoDB::Table" || resource.type == "aws_db_instance" || resource.type == "aws_dynamodb_table") &&
    resource.encryption_enabled == false
};

// -----------------------------------------------------------------------------
// RULE 6: Serverless Least-Privilege Execution Role
// Forbids Lambda functions configured with administrative or wildcard execution roles.
// -----------------------------------------------------------------------------
@id("no-unrestricted-lambda")
forbid(principal, action, resource)
when {
    (resource.type == "AWS::Serverless::Function" || resource.type == "AWS::Lambda::Function" || resource.type == "aws_lambda_function") &&
    resource.has_admin_access == true
};
