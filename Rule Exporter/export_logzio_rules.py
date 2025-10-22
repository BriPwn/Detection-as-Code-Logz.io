#!/usr/bin/env python3
"""
Logz.io Rules Exporter (Enhanced)
Exports all rules from Logz.io API to individual JSON files
Now with command-line arguments!
"""

import os
import sys
import json
import requests
from pathlib import Path
import re
import argparse

# Configuration
LOGZIO_API_TOKEN = os.environ.get('LOGZIO_API_TOKEN')
LOGZIO_API_URL = os.environ.get('LOGZIO_API_URL', 'https://api.logz.io/v2')

# API endpoints to try
ENDPOINTS = [
    '/security/rules/search',
    '/siem/rules/search',
    '/correlation-rules/search'
]

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Export Logz.io security rules to individual JSON files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export rules with tag 'psdo-dev'
  python3 export_logzio_rules_enhanced.py --tag psdo-dev

  # Export ALL rules (no filter)
  python3 export_logzio_rules_enhanced.py --all

  # Export rules with multiple tags
  python3 export_logzio_rules_enhanced.py --tag prod --tag security

  # Export to custom directory
  python3 export_logzio_rules_enhanced.py --tag psdo-dev --output my-rules

  # Export with custom page size
  python3 export_logzio_rules_enhanced.py --all --page-size 500
        """
    )
    
    parser.add_argument(
        '--tag', '-t',
        action='append',
        dest='tags',
        help='Tag to filter rules (can be used multiple times for multiple tags)'
    )
    
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Export ALL rules (ignore tag filters)'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='exported-rules',
        help='Output directory (default: exported-rules)'
    )
    
    parser.add_argument(
        '--page-size',
        type=int,
        default=1000,
        help='Number of rules per page (default: 1000)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Validation
    if not args.all and not args.tags:
        parser.error("Must specify either --tag or --all")
    
    if args.all and args.tags:
        parser.error("Cannot use --all and --tag together")
    
    return args

def validate_environment():
    """Validate required environment variables"""
    if not LOGZIO_API_TOKEN:
        print("❌ Error: LOGZIO_API_TOKEN environment variable is required")
        print("   Set it with: export LOGZIO_API_TOKEN='your-token-here'")
        sys.exit(1)
    
    print(f"✅ API Token: {'*' * 20}{LOGZIO_API_TOKEN[-4:]}")
    print(f"✅ API URL: {LOGZIO_API_URL}")
    print()

def create_output_directory(output_dir):
    """Create output directory if it doesn't exist"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directory: {output_dir}\n")

def sanitize_filename(title):
    """Convert rule title to a safe filename"""
    # Remove or replace invalid characters
    safe_title = re.sub(r'[<>:"/\\|?*]', '-', title)
    # Remove extra spaces and limit length
    safe_title = re.sub(r'\s+', '-', safe_title.strip())
    safe_title = safe_title[:100]  # Limit filename length
    return safe_title

def fetch_rules(tags=None, page_size=1000, verbose=False):
    """Fetch all rules from Logz.io API with pagination"""
    headers = {
        'X-API-TOKEN': LOGZIO_API_TOKEN,
        'Content-Type': 'application/json'
    }
    
    # Build payload
    payload = {
        "filter": {},
        "pagination": {
            "pageNumber": 1,
            "pageSize": page_size
        }
    }
    
    # Add tag filter if specified
    if tags:
        payload["filter"]["tags"] = tags
        print(f"🔍 Searching for rules with tags: {', '.join(tags)}")
    else:
        print(f"🔍 Searching for ALL rules (no tag filter)")
    
    print(f"📊 Page size: {page_size}\n")
    
    all_rules = []
    current_page = 1
    
    # Try different endpoints
    for endpoint in ENDPOINTS:
        url = f"{LOGZIO_API_URL}{endpoint}"
        if verbose:
            print(f"🔗 Trying endpoint: {url}")
        
        try:
            payload['pagination']['pageNumber'] = 1
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Connected to {endpoint}\n")
                
                # Pagination loop
                while True:
                    print(f"📄 Fetching page {current_page}...", end=" ")
                    
                    response = requests.post(url, headers=headers, json=payload, timeout=30)
                    
                    if response.status_code != 200:
                        print(f"\n❌ Error on page {current_page}: {response.status_code}")
                        if verbose:
                            print(f"Response: {response.text}")
                        break
                    
                    data = response.json()
                    
                    # Handle different response structures
                    if 'results' in data:
                        rules = data['results']
                    elif 'data' in data:
                        rules = data['data']
                    else:
                        rules = data if isinstance(data, list) else []
                    
                    if not rules:
                        print("(empty)")
                        break
                    
                    print(f"✅ {len(rules)} rules")
                    all_rules.extend(rules)
                    
                    # Check if there are more pages
                    total_rules = data.get('pagination', {}).get('total', len(all_rules))
                    if len(all_rules) >= total_rules:
                        break
                    
                    # Move to next page
                    current_page += 1
                    payload['pagination']['pageNumber'] = current_page
                
                return all_rules
            
            elif response.status_code == 404:
                if verbose:
                    print(f"⚠️  Endpoint not found (404), trying next...\n")
                continue
            else:
                if verbose:
                    print(f"⚠️  Status {response.status_code}, trying next...\n")
                continue
                
        except requests.exceptions.RequestException as e:
            if verbose:
                print(f"⚠️  Connection error: {e}\n")
            continue
    
    print("❌ Failed to fetch rules from all endpoints")
    return None

def save_rules_to_files(rules, output_dir, verbose=False):
    """Save each rule to a separate JSON file"""
    if not rules:
        print("⚠️  No rules to save")
        return
    
    print(f"\n💾 Saving {len(rules)} rules to individual files...\n")
    
    saved_count = 0
    failed_count = 0
    
    for idx, rule in enumerate(rules, 1):
        try:
            # Get rule title for filename
            title = rule.get('title', rule.get('name', f'rule-{idx}'))
            rule_id = rule.get('id', idx)
            
            # Create safe filename
            safe_title = sanitize_filename(title)
            filename = f"{rule_id}_{safe_title}.json"
            filepath = os.path.join(output_dir, filename)
            
            # Save rule to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(rule, f, indent=2, ensure_ascii=False)
            
            if verbose or idx % 50 == 0 or idx == len(rules):
                print(f"  ✅ [{idx}/{len(rules)}] {filename}")
            saved_count += 1
            
        except Exception as e:
            print(f"  ❌ [{idx}/{len(rules)}] Failed to save rule: {e}")
            failed_count += 1
    
    print(f"\n{'='*60}")
    print(f"📊 EXPORT SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successfully saved: {saved_count}/{len(rules)}")
    if failed_count > 0:
        print(f"❌ Failed: {failed_count}/{len(rules)}")
    print(f"📁 Location: {os.path.abspath(output_dir)}")
    print(f"{'='*60}\n")

def main():
    """Main execution function"""
    # Parse arguments
    args = parse_arguments()
    
    print("\n" + "="*60)
    print("🚀 Logz.io Rules Exporter (Enhanced)")
    print("="*60 + "\n")
    
    # Validate environment
    validate_environment()
    
    # Create output directory
    create_output_directory(args.output)
    
    # Determine tag filter
    tags = None if args.all else args.tags
    
    # Fetch rules
    rules = fetch_rules(tags=tags, page_size=args.page_size, verbose=args.verbose)
    
    if rules is None:
        print("\n❌ Export failed - could not fetch rules")
        sys.exit(1)
    
    if not rules:
        print("\n⚠️  No rules found with the specified filter")
        sys.exit(0)
    
    # Save rules to files
    save_rules_to_files(rules, args.output, verbose=args.verbose)
    
    print("✅ Export completed successfully!\n")

if __name__ == "__main__":
    main()
