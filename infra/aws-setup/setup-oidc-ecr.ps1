<#
.SYNOPSIS
    AWS ECR 리포지토리 및 GitHub Actions용 OIDC 설정 자동화 스크립트

.DESCRIPTION
    이 스크립트는 '쇼특허' 프로젝트에 필요한 AWS 환경을 자동으로 구성합니다:
    1. ECR 리포지토리 생성 (staging, prod)
    2. GitHub Actions용 IAM OIDC Identity Provider 생성
    3. `github-actions-oidc-role` IAM 역할 생성 및 권한 연결
#>

# 기본 변수 설정
$GitRepoName = "gksshing/SKN22-4th-2Team" # 변경 금지
$StagingRepo = "short-cut-api-staging"
$ProdRepo = "short-cut-api-prod"
$RoleName = "github-actions-oidc-role"

Write-Host "🚀 AWS 인프라 자동 구성을 시작합니다..." -ForegroundColor Cyan

# 1. AWS Account ID 획득
$AccountId = (aws sts get-caller-identity --query Account --output text).Trim()
$Region = (aws configure get region).Trim()
if ([string]::IsNullOrWhiteSpace($Region)) { $Region = "ap-northeast-2" }

Write-Host "✅ AWS 연결 확인: Account=$AccountId, Region=$Region" -ForegroundColor Green

# 2. ECR 리포지토리 생성
function Create-ECRRepository {
    param([string]$RepoName)
    
    $check = aws ecr describe-repositories --repository-names $RepoName 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "➡️ ECR 리포지토리 [$RepoName] 는 이미 존재합니다. (Skip)" -ForegroundColor Yellow
    } else {
        Write-Host "🆕 ECR 리포지토리 [$RepoName] 생성 중..."
        $null = aws ecr create-repository --repository-name $RepoName `
            --image-scanning-configuration scanOnPush=true `
            --image-tag-mutability MUTABLE
        Write-Host "✅ ECR 리포지토리 [$RepoName] 생성 완료!" -ForegroundColor Green
    }
}

Create-ECRRepository -RepoName $StagingRepo
Create-ECRRepository -RepoName $ProdRepo

# 3. IAM OIDC Provider 생성
$OidcUrl = "https://token.actions.githubusercontent.com"
$ProviderArn = "arn:aws:iam::${AccountId}:oidc-provider/token.actions.githubusercontent.com"

$checkProvider = aws iam get-open-id-connect-provider --open-id-connect-provider-arn $ProviderArn 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "➡️ GitHub OIDC Provider는 이미 존재합니다. (Skip)" -ForegroundColor Yellow
} else {
    Write-Host "🆕 GitHub OIDC Provider 생성 중..."
    
    # GitHub OIDC Thumbprint 획득 (고정값 또는 동적조회. 현재 공식 썸프린트 2개 허용 권장)
    # Ref: https://github.blog/changelog/2023-06-27-github-actions-update-on-oidc-integration-with-aws/
    $Thumbprint1 = "6938fd4d98bab03faadb97b34396831e3780aea1"
    $Thumbprint2 = "1c58a3a8518e8759bf075b76b750d4f2df264fcd"

    $null = aws iam create-open-id-connect-provider `
        --url $OidcUrl `
        --client-id-list "sts.amazonaws.com" `
        --thumbprint-list $Thumbprint1 $Thumbprint2
    Write-Host "✅ GitHub OIDC Provider 생성 완료!" -ForegroundColor Green
}

# 4. IAM Role 생성
$TrustPolicyJson = @"
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "$ProviderArn"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:${GitRepoName}:*"
                }
            }
        }
    ]
}
"@

$TrustPolicyPath = "infra\aws-setup\trust-policy.json"
$TrustPolicyJson | Out-File -FilePath $TrustPolicyPath -Encoding utf8

$checkRole = aws iam get-role --role-name $RoleName 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "➡️ IAM Role [$RoleName] 는 이미 존재합니다. Trust Policy를 업데이트합니다." -ForegroundColor Yellow
    $null = aws iam update-assume-role-policy --role-name $RoleName --policy-document "file://$TrustPolicyPath"
} else {
    Write-Host "🆕 IAM Role [$RoleName] 생성 중..."
    $null = aws iam create-role --role-name $RoleName --assume-role-policy-document "file://$TrustPolicyPath"
    Write-Host "✅ IAM Role [$RoleName] 생성 완료!" -ForegroundColor Green
}

# 5. ECR Push Policy 생성 및 Role 연결
# 보안을 위해 컨테이너 서비스, ECR 액세스, Logs 등 기본 권한 관리
$PolicyArn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser"
Write-Host "🔗 IAM Role에 ECR 정책($PolicyArn) 연결 중..."
$null = aws iam attach-role-policy --role-name $RoleName --policy-arn $PolicyArn

Write-Host "🎉 모든 인프라 구성이 완료되었습니다!" -ForegroundColor Cyan
Write-Host "============================================="
Write-Host "📌 GitHub Secrets에 등록할 내용:"
Write-Host "AWS_ACCOUNT_ID: $AccountId"
Write-Host "AWS_REGION    : $Region"
Write-Host "ECR_REPO_STAGING: $StagingRepo"
Write-Host "ECR_REPO_PROD   : $ProdRepo"
Write-Host "============================================="
