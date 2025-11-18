# Add AWS credentials to existing secret
$secretName = "bad-apples-backend-task-secrets"
$region = "us-east-1"

Write-Host "Getting current secret..." -ForegroundColor Blue

# Get current secret
$currentSecret = aws secretsmanager get-secret-value `
    --secret-id $secretName `
    --query SecretString `
    --output text `
    --region $region

# Parse JSON and add AWS credentials
$json = $currentSecret | ConvertFrom-Json
$json | Add-Member -MemberType NoteProperty -Name 'AWS_ACCESS_KEY_ID' -Value '' -Force
$json | Add-Member -MemberType NoteProperty -Name 'AWS_SECRET_ACCESS_KEY' -Value '' -Force

# Convert back to JSON
$updatedSecret = $json | ConvertTo-Json -Compress

Write-Host "Updating secret with AWS credentials fields..." -ForegroundColor Blue

# Update secret
aws secretsmanager update-secret `
    --secret-id $secretName `
    --secret-string $updatedSecret `
    --region $region

Write-Host "✓ Secret updated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now set the values using:" -ForegroundColor Yellow
Write-Host "  ./update-secrets.sh" -ForegroundColor Cyan
Write-Host "  or" -ForegroundColor Yellow
Write-Host "  terraform apply" -ForegroundColor Cyan

