#!/usr/bin/env python3
"""
Logz.io Rules Validator (Fixed)
Validates Logz.io security rule files locally before deployment
Now matches the ACTUAL Logz.io rule structure!
"""

import json
import yaml
import sys
import os
import argparse
from pathlib import Path
from typing import Dict, List, Any

class LogzioRuleValidator:
    """Validates Logz.io security rule configuration files"""
    
    def __init__(self, rules_dir: str = "logzio-rules"):
        self.rules_dir = Path(rules_dir)
        self.errors = []
        self.warnings = []
        
    def validate_json_syntax(self, file_path: Path) -> bool:
        """Validate JSON file syntax"""
        try:
            with open(file_path, 'r') as f:
                json.load(f)
            return True
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON syntax error in {file_path}: {e}")
            return False
            
    def validate_yaml_syntax(self, file_path: Path) -> bool:
        """Validate YAML file syntax"""
        try:
            with open(file_path, 'r') as f:
                yaml.safe_load(f)
            return True
        except yaml.YAMLError as e:
            self.errors.append(f"YAML syntax error in {file_path}: {e}")
            return False
    
    def validate_security_rule(self, rule: Dict[str, Any], file_path: Path) -> bool:
        """Validate Logz.io security rule structure and required fields"""
        valid = True
        
        # Core required fields
        required_fields = ['title', 'enabled', 'searchTimeFrameMinutes', 'subComponents']
        
        for field in required_fields:
            if field not in rule:
                self.errors.append(f"Missing required field '{field}' in {file_path}")
                valid = False
        
        # Validate title
        if 'title' in rule:
            if not rule['title'] or not isinstance(rule['title'], str):
                self.errors.append(f"'title' must be a non-empty string in {file_path}")
                valid = False
        
        # Validate enabled
        if 'enabled' in rule:
            if not isinstance(rule['enabled'], bool):
                self.errors.append(f"'enabled' must be a boolean in {file_path}")
                valid = False
        
        # Validate searchTimeFrameMinutes
        if 'searchTimeFrameMinutes' in rule:
            if not isinstance(rule['searchTimeFrameMinutes'], (int, float)):
                self.errors.append(f"'searchTimeFrameMinutes' must be a number in {file_path}")
                valid = False
            elif rule['searchTimeFrameMinutes'] <= 0:
                self.errors.append(f"'searchTimeFrameMinutes' must be positive in {file_path}")
                valid = False
        
        # Validate output structure
        if 'output' in rule:
            if not self.validate_output(rule['output'], file_path):
                valid = False
        else:
            self.warnings.append(f"Missing 'output' field in {file_path} - rule won't send notifications")
        
        # Validate subComponents (this is critical!)
        if 'subComponents' in rule:
            if not isinstance(rule['subComponents'], list):
                self.errors.append(f"'subComponents' must be a list in {file_path}")
                valid = False
            elif len(rule['subComponents']) == 0:
                self.errors.append(f"'subComponents' cannot be empty in {file_path}")
                valid = False
            else:
                for idx, component in enumerate(rule['subComponents']):
                    if not self.validate_subcomponent(component, idx, file_path):
                        valid = False
        
        # Validate correlations if present
        if 'correlations' in rule:
            if not self.validate_correlations(rule['correlations'], file_path):
                valid = False
        
        # Validate tags
        if 'tags' in rule:
            if not isinstance(rule['tags'], list):
                self.errors.append(f"'tags' must be a list in {file_path}")
                valid = False
        
        # Check for recommended fields
        if 'description' not in rule or not rule.get('description'):
            self.warnings.append(f"Missing or empty 'description' in {file_path}")
        
        if 'tags' not in rule or not rule.get('tags'):
            self.warnings.append(f"No tags defined in {file_path} - consider adding tags for organization")
        
        # Check for read-only fields that shouldn't be in new rules
        readonly_fields = ['id', 'createdAt', 'createdBy', 'updatedAt', 'updatedBy']
        for field in readonly_fields:
            if field in rule:
                self.warnings.append(
                    f"Read-only field '{field}' found in {file_path} - "
                    "this will be ignored on creation"
                )
        
        return valid
    
    def validate_output(self, output: Dict[str, Any], file_path: Path) -> bool:
        """Validate output configuration"""
        valid = True
        
        if 'recipients' not in output:
            self.warnings.append(f"No 'recipients' in output for {file_path}")
            return True
        
        recipients = output['recipients']
        
        # Check for at least one notification method
        has_emails = recipients.get('emails') and len(recipients['emails']) > 0
        has_endpoints = recipients.get('notificationEndpointIds') and len(recipients['notificationEndpointIds']) > 0
        
        if not has_emails and not has_endpoints:
            self.warnings.append(
                f"No notification recipients (emails or endpoints) configured in {file_path}"
            )
        
        # Validate emails format
        if 'emails' in recipients:
            if not isinstance(recipients['emails'], list):
                self.errors.append(f"'emails' must be a list in {file_path}")
                valid = False
            else:
                for email in recipients['emails']:
                    if '@' not in email:
                        self.warnings.append(f"Invalid email format: {email} in {file_path}")
        
        # Validate suppressNotificationsMinutes
        if 'suppressNotificationsMinutes' in output:
            if not isinstance(output['suppressNotificationsMinutes'], (int, float)):
                self.errors.append(
                    f"'suppressNotificationsMinutes' must be a number in {file_path}"
                )
                valid = False
        else:
            self.warnings.append(
                f"Consider adding 'suppressNotificationsMinutes' in {file_path} to avoid alert fatigue"
            )
        
        return valid
    
    def validate_subcomponent(self, component: Dict[str, Any], idx: int, file_path: Path) -> bool:
        """Validate a subComponent"""
        valid = True
        component_ref = f"subComponents[{idx}]"
        
        # Required fields in subComponent
        if 'queryDefinition' not in component:
            self.errors.append(f"Missing 'queryDefinition' in {component_ref} of {file_path}")
            valid = False
        else:
            if not self.validate_query_definition(component['queryDefinition'], component_ref, file_path):
                valid = False
        
        if 'trigger' not in component:
            self.errors.append(f"Missing 'trigger' in {component_ref} of {file_path}")
            valid = False
        else:
            if not self.validate_trigger(component['trigger'], component_ref, file_path):
                valid = False
        
        return valid
    
    def validate_query_definition(self, query_def: Dict[str, Any], component_ref: str, file_path: Path) -> bool:
        """Validate queryDefinition structure"""
        valid = True
        
        # Check for query
        if 'query' not in query_def:
            self.errors.append(f"Missing 'query' in {component_ref}.queryDefinition of {file_path}")
            valid = False
        elif not query_def['query']:
            self.warnings.append(f"Empty query in {component_ref}.queryDefinition of {file_path}")
        
        # Check aggregation
        if 'aggregation' in query_def:
            agg = query_def['aggregation']
            if 'aggregationType' in agg:
                valid_types = ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'UNIQUE_COUNT', 'NONE']
                if agg['aggregationType'] not in valid_types:
                    self.errors.append(
                        f"Invalid aggregationType '{agg['aggregationType']}' in {component_ref} of {file_path}. "
                        f"Must be one of: {', '.join(valid_types)}"
                    )
                    valid = False
        
        # Validate filters structure if present
        if 'filters' in query_def:
            if not isinstance(query_def['filters'], dict):
                self.errors.append(f"'filters' must be an object in {component_ref} of {file_path}")
                valid = False
        
        # Check groupBy
        if 'groupBy' in query_def:
            if not isinstance(query_def['groupBy'], list):
                self.errors.append(f"'groupBy' must be a list in {component_ref} of {file_path}")
                valid = False
        
        return valid
    
    def validate_trigger(self, trigger: Dict[str, Any], component_ref: str, file_path: Path) -> bool:
        """Validate trigger configuration"""
        valid = True
        
        # Check operator
        if 'operator' not in trigger:
            self.errors.append(f"Missing 'operator' in {component_ref}.trigger of {file_path}")
            valid = False
        else:
            valid_operators = [
                'GREATER_THAN', 'LESS_THAN', 'EQUALS', 'NOT_EQUALS',
                'GREATER_THAN_OR_EQUALS', 'LESS_THAN_OR_EQUALS'
            ]
            if trigger['operator'] not in valid_operators:
                self.errors.append(
                    f"Invalid operator '{trigger['operator']}' in {component_ref}.trigger of {file_path}. "
                    f"Must be one of: {', '.join(valid_operators)}"
                )
                valid = False
        
        # Check severityThresholdTiers
        if 'severityThresholdTiers' not in trigger:
            self.errors.append(f"Missing 'severityThresholdTiers' in {component_ref}.trigger of {file_path}")
            valid = False
        else:
            tiers = trigger['severityThresholdTiers']
            if not isinstance(tiers, dict):
                self.errors.append(
                    f"'severityThresholdTiers' must be an object in {component_ref}.trigger of {file_path}"
                )
                valid = False
            else:
                valid_severities = ['LOW', 'MEDIUM', 'HIGH', 'SEVERE']
                for severity, threshold in tiers.items():
                    if severity not in valid_severities:
                        self.errors.append(
                            f"Invalid severity '{severity}' in {component_ref}.trigger of {file_path}. "
                            f"Must be one of: {', '.join(valid_severities)}"
                        )
                        valid = False
                    if not isinstance(threshold, (int, float)):
                        self.errors.append(
                            f"Threshold for {severity} must be a number in {component_ref}.trigger of {file_path}"
                        )
                        valid = False
        
        return valid
    
    def validate_correlations(self, correlations: Dict[str, Any], file_path: Path) -> bool:
        """Validate correlations structure"""
        valid = True
        
        if 'correlationOperators' in correlations:
            if not isinstance(correlations['correlationOperators'], list):
                self.errors.append(f"'correlationOperators' must be a list in {file_path}")
                valid = False
            else:
                valid_operators = ['AND', 'OR']
                for op in correlations['correlationOperators']:
                    if op not in valid_operators:
                        self.errors.append(
                            f"Invalid correlation operator '{op}' in {file_path}. "
                            f"Must be one of: {', '.join(valid_operators)}"
                        )
                        valid = False
        
        if 'joins' in correlations:
            if not isinstance(correlations['joins'], list):
                self.errors.append(f"'joins' must be a list in {file_path}")
                valid = False
        
        return valid
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate a single rule file"""
        if not file_path.exists():
            self.errors.append(f"File not found: {file_path}")
            return False
        
        # Check syntax based on extension
        if file_path.suffix == '.json':
            if not self.validate_json_syntax(file_path):
                return False
            
            # Load and validate content
            with open(file_path, 'r') as f:
                rule = json.load(f)
            
            # Validate as security rule
            return self.validate_security_rule(rule, file_path)
                
        elif file_path.suffix in ['.yaml', '.yml']:
            if not self.validate_yaml_syntax(file_path):
                return False
            
            # Load and validate content
            with open(file_path, 'r') as f:
                rule = yaml.safe_load(f)
            
            # Validate as security rule
            return self.validate_security_rule(rule, file_path)
        
        return True
    
    def validate_all(self) -> bool:
        """Validate all rule files in the rules directory"""
        if not self.rules_dir.exists():
            self.errors.append(f"Rules directory not found: {self.rules_dir}")
            return False
        
        all_valid = True
        file_count = 0
        
        # Find all JSON and YAML files
        for pattern in ['**/*.json', '**/*.yaml', '**/*.yml']:
            for file_path in self.rules_dir.glob(pattern):
                file_count += 1
                print(f"Validating: {file_path}")
                if not self.validate_file(file_path):
                    all_valid = False
        
        if file_count == 0:
            self.warnings.append(f"No rule files found in {self.rules_dir}")
        
        return all_valid
    
    def print_report(self):
        """Print validation report"""
        print("\n" + "="*60)
        print("VALIDATION REPORT")
        print("="*60)
        
        if not self.errors and not self.warnings:
            print("✅ All validations passed!")
        else:
            if self.errors:
                print(f"\n❌ ERRORS ({len(self.errors)}):")
                for error in self.errors:
                    print(f"  - {error}")
            
            if self.warnings:
                print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
                for warning in self.warnings:
                    print(f"  - {warning}")
        
        print("="*60)
        
        return len(self.errors) == 0


def main():
    parser = argparse.ArgumentParser(
        description='Validate Logz.io security rule files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate all rules in default directory
  python3 validate-rules-fixed.py

  # Validate specific file
  python3 validate-rules-fixed.py --file my-rule.json

  # Validate custom directory
  python3 validate-rules-fixed.py --rules-dir exported-rules

  # Treat warnings as errors
  python3 validate-rules-fixed.py --strict
        """
    )
    parser.add_argument(
        '--rules-dir',
        default='logzio-rules',
        help='Directory containing rule files (default: logzio-rules)'
    )
    parser.add_argument(
        '--file',
        help='Validate a specific file instead of all rules'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat warnings as errors'
    )
    
    args = parser.parse_args()
    
    validator = LogzioRuleValidator(args.rules_dir)
    
    if args.file:
        print(f"Validating single file: {args.file}\n")
        valid = validator.validate_file(Path(args.file))
    else:
        print(f"Validating all rules in: {args.rules_dir}\n")
        valid = validator.validate_all()
    
    success = validator.print_report()
    
    if args.strict and validator.warnings:
        print("\n⚠️  Strict mode enabled - treating warnings as errors")
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
