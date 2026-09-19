"""
CloudSentinel Multi-Format IaC Parser
Extracts cloud resources from Terraform, CloudFormation, and AWS SAM templates,
normalizing them into strongly-typed Cedar entities for policy evaluation.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml

from cloudsentinel.core.models import IaCFormat


class IaCParser:
    """
    Parses CloudFormation, AWS SAM, and Terraform IaC definitions
    into normalized Cedar entity representations.
    """

    @staticmethod
    def detect_format(file_path: Path, content: str) -> IaCFormat:
        """Detect the IaC format from file extension and content hints."""
        name_lower = file_path.name.lower()
        if name_lower.endswith(".tf") or name_lower.endswith(".tf.json"):
            return IaCFormat.TERRAFORM

        # Check YAML / JSON content for CloudFormation / SAM
        if "AWS::Serverless" in content or "Transform: AWS::Serverless" in content:
            return IaCFormat.SAM
        if "AWSTemplateFormatVersion" in content or "Resources" in content:
            return IaCFormat.CLOUDFORMATION

        # Default heuristic based on suffix
        if suffix in [".yaml", ".yml"]:
            return IaCFormat.SAM if "Serverless" in content else IaCFormat.CLOUDFORMATION
        if suffix == ".json":
            return IaCFormat.CLOUDFORMATION

        return IaCFormat.UNKNOWN

    def parse(self, file_path: Path) -> Tuple[IaCFormat, List[Dict[str, Any]]]:
        """
        Parses an IaC file and returns its detected format and Cedar entities list.
        """
        resolved = file_path.resolve()
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        iac_format = self.detect_format(resolved, content)

        if iac_format in (IaCFormat.CLOUDFORMATION, IaCFormat.SAM):
            raw_data = self._parse_yaml_or_json(content)
            entities = self._extract_cfn_sam_entities(raw_data)
        elif iac_format == IaCFormat.TERRAFORM:
            entities = self._extract_terraform_entities(content, resolved)
        else:
            # Attempt best-effort CFN/SAM parse
            raw_data = self._parse_yaml_or_json(content)
            entities = self._extract_cfn_sam_entities(raw_data)

        return iac_format, entities

    def _parse_yaml_or_json(self, content: str) -> Dict[str, Any]:
        """Parses YAML or JSON content, ignoring CloudFormation short tags."""
        try:
            # Custom YAML loader to handle CloudFormation intrinsic functions (!Sub, !Ref, !GetAtt, etc.)
            class CFNLoader(yaml.SafeLoader):
                pass

            tags = [
                "!Ref", "!Sub", "!GetAtt", "!Join", "!Select", "!Split",
                "!FindInMap", "!Base64", "!Cidr", "!And", "!Equals", "!If",
                "!Not", "!Or", "!Condition", "!ImportValue"
            ]
            for tag in tags:
                yaml.add_constructor(
                    tag,
                    lambda loader, node: loader.construct_scalar(node)
                    if isinstance(node, yaml.ScalarNode)
                    else loader.construct_sequence(node)
                    if isinstance(node, yaml.SequenceNode)
                    else loader.construct_mapping(node),
                    Loader=CFNLoader,
                )

            data = yaml.load(content, Loader=CFNLoader)
            return data if isinstance(data, dict) else {}
        except Exception:
            try:
                return json.loads(content)
            except Exception:
                return {}

    def _extract_cfn_sam_entities(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normalizes CloudFormation / SAM resources into Cedar entities."""
        entities: List[Dict[str, Any]] = []
        resources = data.get("Resources", {})
        if not isinstance(resources, dict):
            return entities

        for logical_id, res in resources.items():
            if not isinstance(res, dict):
                continue
            res_type = res.get("Type", "")
            properties = res.get("Properties", {}) or {}

            attrs: Dict[str, Any] = {
                "type": res_type,
                "logical_id": logical_id,
            }

            # AWS::S3::Bucket
            if res_type == "AWS::S3::Bucket":
                acl = str(properties.get("AccessControl", "")).lower()
                pab = properties.get("PublicAccessBlockConfiguration", {})
                is_public = False
                public_access_block = True

                if "public" in acl:
                    is_public = True

                if not pab or not all([
                    pab.get("BlockPublicAcls", False) is True,
                    pab.get("BlockPublicPolicy", False) is True,
                    pab.get("IgnorePublicAcls", False) is True,
                    pab.get("RestrictPublicBuckets", False) is True,
                ]):
                    public_access_block = False

                encryption = properties.get("BucketEncryption", {})
                encryption_enabled = bool(encryption)

                attrs.update({
                    "is_public": is_public,
                    "public_access_block": public_access_block,
                    "encryption_enabled": encryption_enabled,
                })

            # AWS::IAM::Role & AWS::IAM::Policy
            elif res_type in ("AWS::IAM::Role", "AWS::IAM::Policy"):
                managed_policies = properties.get("ManagedPolicyArns", [])
                if isinstance(managed_policies, str):
                    managed_policies = [managed_policies]

                has_admin = any("AdministratorAccess" in str(arn) for arn in managed_policies)
                has_wildcard = self._check_policy_statements_for_wildcards(properties)

                attrs.update({
                    "has_admin_access": has_admin,
                    "has_wildcard_policy": has_wildcard,
                })

            # AWS::EC2::SecurityGroup
            elif res_type == "AWS::EC2::SecurityGroup":
                ingress_rules = properties.get("SecurityGroupIngress", [])
                has_wildcard_ingress = False
                if isinstance(ingress_rules, list):
                    for rule in ingress_rules:
                        if not isinstance(rule, dict):
                            continue
                        cidr = rule.get("CidrIp", "")
                        cidr_v6 = rule.get("CidrIpv6", "")
                        if cidr in ("0.0.0.0/0", "::/0") or cidr_v6 == "::/0":
                            has_wildcard_ingress = True
                            break

                attrs.update({
                    "has_wildcard_ingress": has_wildcard_ingress,
                })

            # AWS::RDS::DBInstance & AWS::DynamoDB::Table
            elif res_type in ("AWS::RDS::DBInstance", "AWS::DynamoDB::Table"):
                storage_encrypted = properties.get("StorageEncrypted", False)
                sse_spec = properties.get("SSESpecification", {})
                sse_enabled = sse_spec.get("SSEEnabled", False) if isinstance(sse_spec, dict) else False

                encryption_enabled = bool(storage_encrypted or sse_enabled)
                attrs.update({
                    "encryption_enabled": encryption_enabled,
                })

            # AWS::Serverless::Function & AWS::Lambda::Function
            elif res_type in ("AWS::Serverless::Function", "AWS::Lambda::Function"):
                policies = properties.get("Policies", [])
                if isinstance(policies, str):
                    policies = [policies]
                has_admin = any("AdministratorAccess" in str(p) for p in policies)

                attrs.update({
                    "has_admin_access": has_admin,
                })

            entities.append({
                "uid": {"type": "Resource", "id": logical_id},
                "attrs": attrs,
                "parents": [],
            })

        return entities

    def _extract_terraform_entities(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Extracts entities from Terraform (.tf or .tf.json)."""
        entities: List[Dict[str, Any]] = []

        # If it's a JSON file (.tf.json)
        if file_path.suffix == ".json" or file_path.name.endswith(".tf.json"):
            try:
                tf_data = json.loads(content)
                resource_blocks = tf_data.get("resource", {})
                for res_type, resources in resource_blocks.items():
                    for name, props in resources.items():
                        entity = self._normalize_tf_resource(res_type, name, props)
                        if entity:
                            entities.append(entity)
                return entities
            except Exception:
                pass

        # Robust regex-based HCL parser for standard Terraform configurations
        tf_resources = self._parse_hcl_blocks(content)
        for res_type, name, block_body in tf_resources:
            props = self._parse_hcl_properties(block_body)
            entity = self._normalize_tf_resource(res_type, name, props)
            if entity:
                entities.append(entity)

        return entities

    def _normalize_tf_resource(self, res_type: str, name: str, props: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalizes a single Terraform resource into Cedar attributes."""
        attrs: Dict[str, Any] = {
            "type": res_type,
            "logical_id": name,
        }

        if res_type == "aws_s3_bucket":
            acl = str(props.get("acl", "")).lower()
            is_public = "public" in acl
            # In TF, public access block is often a companion resource or attribute
            public_access_block = props.get("block_public_acls", True) is True
            encryption_enabled = "server_side_encryption_configuration" in props or "sse_algorithm" in str(props)
            attrs.update({
                "is_public": is_public,
                "public_access_block": public_access_block,
                "encryption_enabled": encryption_enabled,
            })

        elif res_type in ("aws_iam_role", "aws_iam_policy"):
            raw_str = str(props)
            has_admin = "AdministratorAccess" in raw_str or ('"Action": "*"' in raw_str and '"Resource": "*"' in raw_str)
            attrs.update({
                "has_admin_access": has_admin,
                "has_wildcard_policy": has_admin,
            })

        elif res_type == "aws_security_group":
            raw_str = str(props)
            has_wildcard = "0.0.0.0/0" in raw_str or "::/0" in raw_str
            attrs.update({
                "has_wildcard_ingress": has_wildcard,
            })

        elif res_type in ("aws_db_instance", "aws_dynamodb_table"):
            storage_encrypted = props.get("storage_encrypted", False)
            attrs.update({
                "encryption_enabled": bool(storage_encrypted or "kms_key_id" in props or "server_side_encryption" in str(props)),
            })

        elif res_type == "aws_lambda_function":
            has_admin = "AdministratorAccess" in str(props)
            attrs.update({
                "has_admin_access": has_admin,
            })
        else:
            return None

        return {
            "uid": {"type": "Resource", "id": name},
            "attrs": attrs,
            "parents": [],
        }

    def _parse_hcl_blocks(self, content: str) -> List[Tuple[str, str, str]]:
        """Extracts resource blocks: resource "type" "name" { ... }"""
        pattern = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{', re.MULTILINE)
        matches = []
        for m in pattern.finditer(content):
            res_type, name = m.group(1), m.group(2)
            start_pos = m.end()
            # Match matching closing brace
            brace_count = 1
            idx = start_pos
            while idx < len(content) and brace_count > 0:
                if content[idx] == "{":
                    brace_count += 1
                elif content[idx] == "}":
                    brace_count -= 1
                idx += 1
            body = content[start_pos : idx - 1]
            matches.append((res_type, name, body))
        return matches

    def _parse_hcl_properties(self, block_body: str) -> Dict[str, Any]:
        """Simple extractor for key-value assignments inside HCL blocks."""
        props: Dict[str, Any] = {}
        for line in block_body.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                props[k] = v
        # Also preserve block text for substring matching
        props["_raw"] = block_body
        return props

    def _check_policy_statements_for_wildcards(self, properties: Dict[str, Any]) -> bool:
        """Inspects IAM policy document statements for wildcard Actions & Resources."""
        doc = properties.get("PolicyDocument") or properties.get("AssumeRolePolicyDocument")
        if not isinstance(doc, dict):
            # Check inline policies
            policies = properties.get("Policies", [])
            if isinstance(policies, list):
                for p in policies:
                    if isinstance(p, dict) and self._check_policy_statements_for_wildcards(p):
                        return True
            return False

        statements = doc.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]
        if not isinstance(statements, list):
            return False

        for stmt in statements:
            if not isinstance(stmt, dict):
                continue
            effect = stmt.get("Effect", "")
            if effect != "Allow":
                continue
            action = stmt.get("Action", [])
            resource = stmt.get("Resource", [])

            action_is_wildcard = action == "*" or (isinstance(action, list) and "*" in action)
            resource_is_wildcard = resource == "*" or (isinstance(resource, list) and "*" in resource)

            if action_is_wildcard and resource_is_wildcard:
                return True

        return False
