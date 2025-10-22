# 🔄 Complete Logz.io Rules Workflow

This guide shows the complete workflow for exporting, validating, cleaning, and deploying Logz.io security rules.

## 📋 Quick Overview

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐      ┌─────────────┐
│   Export    │  →   │   Validate   │  →   │    Clean    │  →   │   Deploy    │
│   Rules     │      │   Structure  │      │  Read-Only  │      │   Back to   │
│  from API   │      │              │      │   Fields    │      │  Logz.io    │
└─────────────┘      └──────────────┘      └─────────────┘      └─────────────┘
```

---

## 🚀 Step 1: Export Rules

Export all your security rules from Logz.io to individual JSON files.

### Using the Enhanced Exporter

```bash
# Set your API token
export LOGZIO_API_TOKEN='your-token-here'

# Export rules with specific tag
python3 export_logzio_rules.py --tag psdo-dev

# OR export ALL rules
python3 export_logzio_rules.py --all --output exported-rules
```

**Output:** Rules saved to `exported-rules/` directory
```
exported-rules/
├── 1716806_Log-Cleared.json
├── 1823456_Suspicious-DNS-Query.json
└── ...
```

---

## ✅ Step 2: Validate Rules

Validate the exported rules to ensure they have correct structure.

```bash
# Validate all rules in directory
python3 validate-rules-fixed.py --rules-dir exported-rules

# Validate a single rule
python3 validate-rules-fixed.py --file exported-rules/1716806_Log-Cleared.json
```

**Expected Output:**
```
============================================================
VALIDATION REPORT
============================================================

⚠️  WARNINGS (5):
  - Read-only field 'id' found in ... (will be ignored on creation)
  - Read-only field 'createdAt' found in ...
  - ...
============================================================
```

These warnings are **normal for exported rules** - the read-only fields will be handled in the next step.

---

## 🧹 Step 3: Clean Rules

Remove read-only fields to prepare rules for re-deployment.

```bash
# Clean all rules in directory (creates cleaned-rules/ folder)
python3 clean-rules.py --dir exported-rules

# Clean all rules in-place (overwrites originals)
python3 clean-rules.py --dir exported-rules --in-place

# Clean single file
python3 clean-rules.py --file my-rule.json
```

**Output:** 
```
============================================================
📊 CLEANING SUMMARY
============================================================
✅ Successfully cleaned: 247
============================================================
```

**Fields Removed:**
- `id` - Auto-generated on creation
- `createdAt` - Auto-generated on creation
- `createdBy` - Auto-generated on creation
- `updatedAt` - Auto-generated on update
- `updatedBy` - Auto-generated on update

---

## 🔍 Step 4: Validate Cleaned Rules

Re-validate to ensure no errors or warnings.

```bash
# Validate cleaned rules
python3 validate-rules-fixed.py --rules-dir cleaned-rules
```

**Expected Output:**
```
============================================================
VALIDATION REPORT
============================================================
✅ All validations passed!
============================================================
```

---

## 🚢 Step 5: Deploy Rules

Deploy the cleaned rules back to Logz.io (using your deployment workflow).

```bash
# Example: Deploy using GitHub Actions workflow
# Push the cleaned rules to your repo and let CI/CD handle deployment

# Or manually deploy with deployment script
export LOGZIO_API_TOKEN='your-token'
export LOGZIO_API_URL='https://api.logz.io/v2'

# Deploy rules from cleaned-rules directory
./deploy-logzio-rules.py --rules-dir cleaned-rules
```

---

## 🔄 Common Workflows

### Workflow A: Backup All Rules

```bash
# 1. Export everything
export LOGZIO_API_TOKEN='your-token'
python3 export_logzio_rules.py --all --output backup-$(date +%Y%m%d)

# 2. Commit to git
git add backup-$(date +%Y%m%d)
git commit -m "Backup rules $(date +%Y-%m-%d)"
git push
```

### Workflow B: Migrate Rules to New Environment

```bash
# 1. Export from source environment
export LOGZIO_API_TOKEN='source-token'
python3 export_logzio_rules.py --all --output source-rules

# 2. Clean for deployment
python3 clean-rules.py --dir source-rules --output deployment-ready

# 3. Validate
python3 validate-rules-fixed.py --rules-dir deployment-ready

# 4. Deploy to target environment
export LOGZIO_API_TOKEN='target-token'
export LOGZIO_API_URL='https://api-eu.logz.io/v2'  # Different region
./deploy-logzio-rules.py --rules-dir deployment-ready
```

### Workflow C: Test Rules Before Deployment

```bash
# 1. Export with dev tag
python3 export_logzio_rules.py --tag dev --output dev-rules

# 2. Clean
python3 clean-rules.py --dir dev-rules --in-place

# 3. Validate with strict mode
python3 validate-rules-fixed.py --rules-dir dev-rules --strict

# 4. If validation passes, deploy
if [ $? -eq 0 ]; then
    echo "✅ Validation passed - ready to deploy"
    ./deploy-logzio-rules.py --rules-dir dev-rules
else
    echo "❌ Validation failed - fix errors before deployment"
fi
```

### Workflow D: Single Rule Modification

```bash
# 1. Export specific rule (export all, then find it)
python3 export_logzio_rules.py --tag my-rule-tag

# 2. Edit the rule JSON file manually
vim exported-rules/1234567_My-Rule.json

# 3. Validate the modified rule
python3 validate-rules-fixed.py --file exported-rules/1234567_My-Rule.json

# 4. Clean it
python3 clean-rules.py --file exported-rules/1234567_My-Rule.json

# 5. Deploy
./deploy-logzio-rules.py --file 1234567_My-Rule_cleaned.json
```

---

## 🛠️ Tool Reference

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `export_logzio_rules.py` | Export rules from API | Logz.io API | JSON files |
| `validate-rules-fixed.py` | Validate rule structure | JSON files | Validation report |
| `clean-rules.py` | Remove read-only fields | JSON files | Cleaned JSON files |
| `deploy-logzio-rules.py` | Deploy rules to API | JSON files | API responses |

---

## 📊 File Structure Example

```
my-logzio-project/
├── exported-rules/          # Raw exports from API
│   ├── 1716806_Log-Cleared.json
│   └── ...
├── cleaned-rules/           # Ready for deployment
│   ├── 1716806_Log-Cleared.json
│   └── ...
├── backups/                 # Version history
│   ├── 2024-10-18/
│   └── 2024-10-17/
└── scripts/
    ├── export_logzio_rules.py
    ├── validate-rules-fixed.py
    ├── clean-rules.py
    └── deploy-logzio-rules.py
```

---

## ⚙️ Environment Variables

```bash
# Required for export and deployment
export LOGZIO_API_TOKEN='your-api-token'

# Optional (defaults shown)
export LOGZIO_API_URL='https://api.logz.io/v2'  # Or EU: api-eu.logz.io/v2
export OUTPUT_DIR='exported-rules'
```

---

## 🔐 Security Best Practices

1. **Never commit API tokens** to git
   ```bash
   echo "*.token" >> .gitignore
   echo ".env" >> .gitignore
   ```

2. **Use environment variables**
   ```bash
   # Store in .env file (gitignored)
   echo "LOGZIO_API_TOKEN=your-token" > .env
   source .env
   ```

3. **Rotate tokens regularly**
   - Generate new token in Logz.io
   - Update environment variable
   - Revoke old token

4. **Use read-only tokens for exports**
   - Export: Only needs "Security - Read"
   - Deploy: Needs "Security - Write"

---

## 🐛 Troubleshooting

### "No rules found"
```bash
# Check if tag is correct (case-sensitive!)
python3 export_logzio_rules.py --tag PSDO-DEV --verbose

# Try exporting all rules
python3 export_logzio_rules.py --all
```

### "Validation failed"
```bash
# Run with verbose output to see what's wrong
python3 validate-rules-fixed.py --file my-rule.json

# Check the specific error message
# Common issues:
# - Missing required fields
# - Invalid operator names
# - Malformed JSON
```

### "Read-only file system"
```bash
# Don't use --in-place on uploaded files
# Instead, specify output path:
python3 clean-rules.py --file /uploaded/rule.json --output ./cleaned-rule.json
```

## 🎯 Summary Checklist

For a complete export → clean → deploy cycle:

- [ ] Set `LOGZIO_API_TOKEN` environment variable
- [ ] Export rules: `python3 export_logzio_rules.py --all`
- [ ] Validate: `python3 validate-rules-fixed.py --rules-dir exported-rules`
- [ ] Clean: `python3 clean-rules.py --dir exported-rules`
- [ ] Re-validate: `python3 validate-rules-fixed.py --rules-dir cleaned-rules`
- [ ] Deploy: Use your deployment workflow
- [ ] Commit to git for version control

**Estimated time:** 5-10 minutes for 100-500 rules

---

**Questions?** Check the tool-specific help:
```bash
python3 export_logzio_rules.py --help
python3 validate-rules-fixed.py --help
python3 clean-rules.py --help
```
Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.