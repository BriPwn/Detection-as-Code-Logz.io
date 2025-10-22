#!/usr/bin/env python3
"""
Clean Exported Logz.io Rules
Removes read-only fields from exported rules to prepare them for re-deployment
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# Fields that are read-only and should be removed
READ_ONLY_FIELDS = [
    'id',
    'createdAt',
    'createdBy', 
    'updatedAt',
    'updatedBy'
]

# Fields that may cause issues in subcomponents
SUBCOMPONENT_READONLY_FIELDS = [
    'id'
]

def clean_rule(rule: Dict[str, Any]) -> Dict[str, Any]:
    """Remove read-only fields from a rule"""
    cleaned = rule.copy()
    
    # Remove top-level read-only fields
    for field in READ_ONLY_FIELDS:
        if field in cleaned:
            del cleaned[field]
    
    # Clean output.recipients if present
    if 'output' in cleaned and 'recipients' in cleaned['output']:
        recipients = cleaned['output']['recipients']
        # Remove notificationEndpointIds if you want to set new ones
        # Uncomment the next line if needed:
        # if 'notificationEndpointIds' in recipients:
        #     del recipients['notificationEndpointIds']
    
    # Clean subComponents
    if 'subComponents' in cleaned:
        for component in cleaned['subComponents']:
            for field in SUBCOMPONENT_READONLY_FIELDS:
                if field in component:
                    del component[field]
    
    return cleaned

def clean_file(input_path: Path, output_path: Path = None, in_place: bool = False):
    """Clean a single rule file"""
    if not input_path.exists():
        print(f"❌ File not found: {input_path}")
        return False
    
    # Load the rule
    with open(input_path, 'r', encoding='utf-8') as f:
        rule = json.load(f)
    
    # Clean it
    cleaned_rule = clean_rule(rule)
    
    # Determine output path
    if in_place:
        output_path = input_path
    elif output_path is None:
        # Create cleaned version with suffix in current directory to avoid read-only issues
        output_path = Path(f"{input_path.stem}_cleaned{input_path.suffix}")
    
    # Save cleaned rule
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_rule, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Cleaned: {input_path} → {output_path}")
    return True

def clean_directory(input_dir: Path, output_dir: Path = None, in_place: bool = False):
    """Clean all JSON files in a directory"""
    if not input_dir.exists():
        print(f"❌ Directory not found: {input_dir}")
        return False
    
    # Create output directory if needed
    if output_dir and not in_place:
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Output directory: {output_dir}\n")
    
    success_count = 0
    fail_count = 0
    
    # Process all JSON files
    for json_file in input_dir.glob('**/*.json'):
        try:
            if output_dir and not in_place:
                # Preserve directory structure
                relative_path = json_file.relative_to(input_dir)
                out_file = output_dir / relative_path
                out_file.parent.mkdir(parents=True, exist_ok=True)
            else:
                out_file = None
            
            if clean_file(json_file, out_file, in_place):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"❌ Error processing {json_file}: {e}")
            fail_count += 1
    
    print(f"\n{'='*60}")
    print(f"📊 CLEANING SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successfully cleaned: {success_count}")
    if fail_count > 0:
        print(f"❌ Failed: {fail_count}")
    print(f"{'='*60}\n")
    
    return fail_count == 0

def main():
    parser = argparse.ArgumentParser(
        description='Clean read-only fields from exported Logz.io rules',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clean a single file (creates new file with _cleaned suffix)
  python3 clean-rules.py --file my-rule.json

  # Clean a file in-place (overwrites original)
  python3 clean-rules.py --file my-rule.json --in-place

  # Clean all files in directory (creates cleaned-rules/ directory)
  python3 clean-rules.py --dir exported-rules

  # Clean directory to specific output directory
  python3 clean-rules.py --dir exported-rules --output deployment-ready

  # Clean directory in-place (overwrites originals)
  python3 clean-rules.py --dir exported-rules --in-place

Read-only fields removed:
  - id
  - createdAt
  - createdBy
  - updatedAt
  - updatedBy
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', '-f', type=Path, help='Clean a single file')
    group.add_argument('--dir', '-d', type=Path, help='Clean all JSON files in directory')
    
    parser.add_argument(
        '--output', '-o', 
        type=Path,
        help='Output directory (only for --dir, default: cleaned-rules)'
    )
    parser.add_argument(
        '--in-place', '-i',
        action='store_true',
        help='Modify files in-place (overwrites originals)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("🧹 Logz.io Rules Cleaner")
    print("="*60 + "\n")
    
    if args.file:
        # Clean single file
        if args.in_place:
            print("⚠️  In-place mode - original file will be overwritten\n")
        success = clean_file(args.file, in_place=args.in_place)
    else:
        # Clean directory
        if args.in_place:
            print("⚠️  In-place mode - original files will be overwritten\n")
            output_dir = None
        elif args.output:
            output_dir = args.output
        else:
            output_dir = Path('cleaned-rules')
        
        success = clean_directory(args.dir, output_dir, args.in_place)
    
    if success:
        print("✅ Cleaning completed successfully!\n")
        sys.exit(0)
    else:
        print("❌ Cleaning completed with errors\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
