# Logz.io Detection as Code

This repository contains a GitHub Actions workflow for automatically deploying security rules to Logz.io.

## 📁 Directory Structure

```
.github/
└── workflows/
    └── deploy-logzio-rules.yml    # Main workflow file

logzio-rules/
├── security/                       # Security rules
│   └── suspicious-activity.json
```

## 🚀 Setup Instructions

### 1. Configure GitHub Secrets

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

#### Required Secrets:
- `LOGZIO_API_TOKEN` - Production Logz.io API token


### 2. Get Your Logz.io API Token

1. Log in to your Logz.io account
2. Navigate to **Settings** → **Manage tokens** → **API tokens**
3. Click **+ New API token**
4. Give it a name (e.g., "GitHub Actions Deployment")
5. Select the appropriate permissions:
   - For security rules: `Security - Read` and `Security - Write`
6. Copy the token and add it to GitHub Secrets

## 📝 Rule File Format

### Security Rules

Security rules should be placed in `logzio-rules/security/` as JSON files.

## 🔄 Workflow Triggers

The workflow is triggered by:

1. **Push to main/master branch** - Automatically deploys rules when changes are pushed to rule files
2. **Pull requests** - Validates rule files without deploying
3. **Manual trigger** - Deploy on-demand with environment selection via Actions tab

## 🎯 Workflow Features

### ✅ Automatic Features
- **Validation** - Validates JSON/YAML syntax before deployment
- **Idempotency** - Updates existing rules or creates new ones based on title
- **Multi-environment support** - Deploy to different environments (prod/staging/dev)
- **Error handling** - Continues with other rules if one fails

### 📊 Deployment Process
1. **Validate** - Check all rule files for valid JSON/YAML syntax
2. **Deploy Security Rules** - Deploy all files in `logzio-rules/security/`


## 🛠️ Usage Examples

### Adding a New Alert Rule

1. Create a new JSON file in `logzio-rules/security/`:
```bash
touch logzio-rules/security/cobaltstrike-usage.json
```
2. Add your rule configuration
3. Commit and push:
```bash
git add logzio-rules/security/cobaltstrike-usage.json
git commit -m "Add Cobalt Strike usage alert rule"
git push origin main
```

### Manual Deployment

1. Go to Actions tab in your GitHub repository
2. Select "Deploy Security Rules" workflow
3. Click "Run workflow"

### Testing Rules in Pull Request

1. Create a new branch:
```bash
git checkout -b add-new-alerts
```

2. Add or modify rules
3. Create a pull request
4. The workflow will validate your rules without deploying

## 🔍 Monitoring Deployments

### Check Workflow Status
- Go to the **Actions** tab in your repository
- Click on the workflow run to see detailed logs
- Each step shows success ✅ or failure ❌ status

## 🐛 Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check if API token is correctly set in GitHub Secrets
2. **404 Not Found**: Verify the API endpoint URL and region configuration
3. **400 Bad Request**: Validate your rule JSON structure
4. **Rate Limiting**: Add delays between deployments if deploying many rules

### Debug Tips

- Check workflow logs in the Actions tab
- Validate JSON locally: `jq . logzio-rules/security-rules/my-rule.json`
- Test API manually with curl:
```bash
curl -X GET \
  -H "X-API-TOKEN: your-token" \
  -H "Content-Type: application/json" \
  https://api.logz.io/v2/alerts
```

## 📚 Additional Resources

- [Logz.io API Documentation](https://docs.logz.io/api/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## 📚 Licensing

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