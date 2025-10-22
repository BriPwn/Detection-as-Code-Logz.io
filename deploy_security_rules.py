#!/usr/bin/env python3
"""
Deploy security rules to Logz.io
Handles JSON cleaning and multi-endpoint deployment with proper error handling
"""

import json
import os
import sys
import copy
from pathlib import Path
from typing import Dict, List, Any, Tuple
import requests


class SecurityRuleDeployer:
    """Handles deployment of security rules to Logz.io"""
    
    def __init__(self, api_token: str, api_url: str, environment: str):
        self.api_token = api_token
        self.api_url = api_url.rstrip('/')
        self.environment = environment
        self.search_endpoint = f"{self.api_url}/security/rules/search"
        self.update_endpoint = f"{self.api_url}/security/rules"
        self.create_endpoints = [
            f"{self.api_url}/security/rules",
            f"{self.api_url}/siem/rules",
            f"{self.api_url}/correlation-rules"
        ]
        
    def clean_rule_json(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove read-only fields that cause 400 errors
        
        Args:
            rule_data: Raw rule JSON data
            
        Returns:
            Cleaned rule data
        """
        # Fields to remove at root level
        readonly_fields = ['id', 'createdAt', 'createdBy', 'updatedAt', 'updatedBy']
        
        # Use deep copy to properly handle nested structures
        # This is important for complex rules with subComponents, correlations, etc.
        cleaned_data = copy.deepcopy(rule_data)
        
        # Remove read-only fields
        for field in readonly_fields:
            cleaned_data.pop(field, None)
        
        # Handle nested notificationEndpointIds if present
        if 'output' in cleaned_data:
            if 'recipients' in cleaned_data['output']:
                if 'notificationEndpointIds' in cleaned_data['output']['recipients']:
                    del cleaned_data['output']['recipients']['notificationEndpointIds']
        
        return cleaned_data
    
    def search_rule_by_title(self, title: str) -> Dict[str, Any]:
        """
        Search for an existing rule by title
        
        Args:
            title: The title of the rule to search for
            
        Returns:
            Dictionary with 'exists' (bool) and 'rule_id' (str or None)
        """
        print(f"🔍 Searching for existing rule with title: '{title}'")
        
        try:
            # Use the correct API format with pagination object
            response = requests.post(
                self.search_endpoint,
                headers={
                    'X-API-TOKEN': self.api_token,
                    'Content-Type': 'application/json'
                },
                json={
                    "filter": {
                        "enabledState": [True]
                    },
                    "pagination": {
                        "pageNumber": 1,
                        "pageSize": 1000
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # The API returns: {"total": int, "results": [...]}
                if isinstance(data, dict) and 'results' in data:
                    results = data['results']
                    total = data.get('total', 0)
                    
                    print(f"   Search returned {len(results)} results (total enabled: {total})")
                    
                    if results and len(results) > 0:
                        # Search through all results for exact title match
                        print(f"   Searching through {len(results)} rules for exact match...")
                        
                        for i, rule in enumerate(results):
                            rule_title = rule.get('title', '')
                            
                            # Debug: show first few comparisons
                            if i < 3:
                                print(f"   [{i+1}] Comparing: '{rule_title[:50]}...' vs '{title[:50]}...'")
                                print(f"       Match: {rule_title == title}")
                            
                            if rule_title == title:
                                rule_id = rule.get('id')
                                print(f"✓ Found existing rule with ID: {rule_id} at position {i+1}")
                                return {'exists': True, 'rule_id': rule_id}
                        
                        # If we get here, no exact match found
                        print(f"✗ No exact title match found (searched {len(results)} result(s))")
                        print(f"   Looking for: '{title}'")
                        print(f"   Length: {len(title)} characters")
                        
                        # Check for case-insensitive or partial matches to help debug
                        similar = []
                        for rule in results[:50]:  # Check first 50
                            rule_title = rule.get('title', '')
                            if title.lower() in rule_title.lower() or rule_title.lower() in title.lower():
                                similar.append({'id': rule.get('id'), 'title': rule_title})
                        
                        if similar:
                            print(f"   💡 Found {len(similar)} similar title(s):")
                            for sim in similar[:3]:
                                print(f"      - ID {sim['id']}: '{sim['title']}'")
                        
                        # If there are more results than we fetched, warn about it
                        if total > len(results):
                            print(f"⚠️  Note: {total - len(results)} more rules exist but weren't searched")
                            print(f"   Consider implementing pagination to search through all {total} rules")
                        
                        return {'exists': False, 'rule_id': None}
                    else:
                        print(f"✗ No enabled rules found in account")
                        return {'exists': False, 'rule_id': None}
                else:
                    # Handle unexpected response format
                    print(f"⚠️ Unexpected response format from search API")
                    print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                    return {'exists': False, 'rule_id': None}
            
            elif response.status_code == 404:
                # Search endpoint might not be available
                print(f"⚠️ Search endpoint not available (404) - will attempt to create new rule")
                return {'exists': False, 'rule_id': None}
            
            else:
                print(f"⚠️ Search returned HTTP {response.status_code}")
                try:
                    print(f"Response: {response.text}")
                except:
                    pass
                return {'exists': False, 'rule_id': None}
        
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Search request failed: {str(e)}")
            print(f"Will attempt to create as new rule")
            return {'exists': False, 'rule_id': None}
        
        except Exception as e:
            print(f"⚠️ Unexpected error during search: {str(e)}")
            return {'exists': False, 'rule_id': None}
    
    def deploy_rule(self, rule_file: Path) -> Tuple[bool, str]:
        """
        Deploy a single security rule (create new or update existing)
        
        Args:
            rule_file: Path to the rule JSON file
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        rule_name = rule_file.stem
        print(f"\n📋 Processing rule: {rule_name}")
        
        try:
            # Load and parse the JSON file
            with open(rule_file, 'r') as f:
                rule_data = json.load(f)
            
            # Get the title from the rule
            rule_title = rule_data.get('title', rule_name)
            
            # Clean the JSON
            cleaned_data = self.clean_rule_json(rule_data)
            
            # Show what we're sending (truncated for debugging)
            json_str = json.dumps(cleaned_data, indent=2)
            print(f"Sending JSON (truncated):")
            print(json_str[:500] + "..." if len(json_str) > 500 else json_str)
            
            # Search for existing rule with this title
            search_result = self.search_rule_by_title(rule_title)
            
            if search_result['exists']:
                # UPDATE existing rule
                rule_id = search_result['rule_id']
                return self._update_rule(rule_id, cleaned_data, rule_name)
            else:
                # CREATE new rule
                return self._create_rule(cleaned_data, rule_name)
        
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in {rule_file}: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error processing {rule_name}: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def _update_rule(self, rule_id: str, rule_data: Dict[str, Any], rule_name: str) -> Tuple[bool, str]:
        """
        Update an existing rule using PUT
        
        Args:
            rule_id: The ID of the rule to update
            rule_data: Cleaned rule data
            rule_name: Name of the rule file
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        update_url = f"{self.update_endpoint}/{rule_id}"
        print(f"\n🔄 Updating existing rule at: {update_url}")
        
        try:
            response = requests.put(
                update_url,
                headers={
                    'X-API-TOKEN': self.api_token,
                    'Content-Type': 'application/json'
                },
                json=rule_data,
                timeout=30
            )
            
            if response.status_code >= 200 and response.status_code < 300:
                print(f"✅ Successfully updated rule (ID: {rule_id})")
                return True, f"Updated successfully (ID: {rule_id})"
            
            else:
                print(f"❌ Update failed with HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error response:")
                    print(json.dumps(error_data, indent=2))
                    
                    error_msg = (
                        error_data.get('message') or 
                        error_data.get('error') or 
                        error_data.get('errorMessage') or
                        'No error message provided'
                    )
                    print(f"Error details: {error_msg}")
                    return False, f"Update failed: {error_msg}"
                except:
                    print(f"Response: {response.text}")
                    return False, f"Update failed with HTTP {response.status_code}"
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Update request failed: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def _create_rule(self, rule_data: Dict[str, Any], rule_name: str) -> Tuple[bool, str]:
        """
        Create a new rule using POST
        
        Args:
            rule_data: Cleaned rule data
            rule_name: Name of the rule file
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        print(f"\n➕ Creating new rule")
        
        # Try each endpoint until one succeeds
        for endpoint in self.create_endpoints:
            print(f"\nTrying endpoint: {endpoint}")
            
            try:
                response = requests.post(
                    endpoint,
                    headers={
                        'X-API-TOKEN': self.api_token,
                        'Content-Type': 'application/json'
                    },
                    json=rule_data,
                    timeout=30
                )
                
                if response.status_code >= 200 and response.status_code < 300:
                    print(f"✅ Successfully created at {endpoint}")
                    try:
                        result = response.json()
                        new_id = result.get('id', 'unknown')
                        return True, f"Created successfully at {endpoint} (ID: {new_id})"
                    except:
                        return True, f"Created successfully at {endpoint}"
                
                elif response.status_code == 400:
                    print(f"❌ Bad Request (400) - Rule format issue")
                    print(f"Error response:")
                    try:
                        error_data = response.json()
                        print(json.dumps(error_data, indent=2))
                        
                        error_msg = (
                            error_data.get('message') or 
                            error_data.get('error') or 
                            error_data.get('errorMessage') or
                            'No error message provided'
                        )
                        print(f"Error details: {error_msg}")
                    except:
                        print(response.text)
                
                elif response.status_code == 404:
                    print(f"Endpoint not found (404) - trying next...")
                
                else:
                    print(f"Failed with HTTP {response.status_code}")
                    try:
                        print(f"Response: {response.text}")
                    except:
                        pass
            
            except requests.exceptions.RequestException as e:
                print(f"Request failed: {str(e)}")
                continue
        
        # If we get here, all endpoints failed
        error_msg = f"""
⚠️ Failed to create {rule_name} at any endpoint

Troubleshooting tips:
1. Check if this is a SIEM correlation rule (not a security rule)
2. Verify the rule structure matches Logz.io's format
3. Ensure notification endpoints exist in your account
4. Check the API token has proper permissions
"""
        print(error_msg)
        return False, f"Failed to create at any endpoint"
    
    def deploy_all_rules(self, rules_directory: str) -> Dict[str, Any]:
        """
        Deploy all rules from a directory
        
        Args:
            rules_directory: Path to directory containing rule JSON files
            
        Returns:
            Dictionary with deployment results
        """
        rules_path = Path(rules_directory)
        
        if not rules_path.exists():
            print(f"❌ Rules directory not found: {rules_directory}")
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'created': 0,
                'updated': 0,
                'failed_rules': []
            }
        
        # Find all JSON files
        rule_files = list(rules_path.glob('*.json'))
        
        if not rule_files:
            print(f"No JSON files found in {rules_directory}")
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'created': 0,
                'updated': 0,
                'failed_rules': []
            }
        
        print(f"🔒 Deploying security rules to {self.environment} environment")
        print(f"Found {len(rule_files)} rule(s) to deploy\n")
        
        results = {
            'total': len(rule_files),
            'successful': 0,
            'failed': 0,
            'created': 0,
            'updated': 0,
            'failed_rules': []
        }
        
        for rule_file in rule_files:
            print("=" * 80)
            success, message = self.deploy_rule(rule_file)
            
            if success:
                results['successful'] += 1
                # Check if it was created or updated
                if 'Updated' in message or 'updated' in message:
                    results['updated'] += 1
                else:
                    results['created'] += 1
            else:
                results['failed'] += 1
                results['failed_rules'].append({
                    'file': rule_file.name,
                    'error': message
                })
        
        return results


def main():
    """Main entry point"""
    
    # Get configuration from environment variables
    api_token = os.environ.get('LOGZIO_API_TOKEN')
    api_url = os.environ.get('LOGZIO_API_URL')
    environment = os.environ.get('DEPLOYMENT_ENV', 'unknown')
    rules_dir = os.environ.get('RULES_DIRECTORY', 'logzio-rules/security')
    
    if not api_token:
        print("❌ Error: LOGZIO_API_TOKEN environment variable is required")
        sys.exit(1)
    
    if not api_url:
        print("❌ Error: LOGZIO_API_URL environment variable is required")
        sys.exit(1)
    
    # Create deployer and run deployment
    deployer = SecurityRuleDeployer(api_token, api_url, environment)
    results = deployer.deploy_all_rules(rules_dir)
    
    # Print summary
    print("\n" + "=" * 80)
    print(f"\n📊 Deployment Summary:")
    print(f"   Total rules: {results['total']}")
    print(f"   ✅ Successful: {results['successful']}")
    print(f"      ➕ Created: {results['created']}")
    print(f"      🔄 Updated: {results['updated']}")
    print(f"   ❌ Failed: {results['failed']}")
    
    if results['failed_rules']:
        print(f"\n⚠️ Failed rules:")
        for failed in results['failed_rules']:
            print(f"   • {failed['file']}: {failed['error']}")
        
        print("\nThis might not be critical - these could be:")
        print("• SIEM correlation rules that need different API")
        print("• Rules with invalid notification endpoints")
        print("• Rules in a different format than expected")
    
    # Exit with error code if any deployments failed
    if results['failed'] > 0:
        sys.exit(1)
    else:
        print("\n✅ All rules deployed successfully!")
        sys.exit(0)


if __name__ == '__main__':
    main()
