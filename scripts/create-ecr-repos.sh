#!/bin/bash
# =============================================================================
# 쇼특허(Short-Cut) – AWS ECR 리포지토리 초기 생성 스크립트
# =============================================================================
# 용도: 프로젝트 초기 1회만 실행. staging/production ECR 리포지토리 생성,
#       이미지 스캔 활성화, 라이프사이클 정책 적용.
#
# 사전 조건:
#   - AWS CLI 설치 및 적절한 권한(ecr:CreateRepository 등) 보유
#   - export AWS_REGION=ap-northeast-2 (또는 아래 변수 직접 수정)
# =============================================================================

set -euo pipefail

# ── 설정 변수 ──────────────────────────────────────────────────────────────
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-263636208782}"
REPO_STAGING="short-cut-api-staging"
REPO_PROD="short-cut-api-prod"

echo "[ECR Setup] AWS 리전: ${AWS_REGION}, 계정 ID: ${AWS_ACCOUNT_ID}"

# ── 라이프사이클 정책 (JSON 인라인) ───────────────────────────────────────
# 규칙 1: untagged(태그 없는) 이미지는 30일 후 자동 삭제
# 규칙 2: tagged 이미지는 최대 30개 보관 (초과 시 오래된 것부터 삭제)
LIFECYCLE_POLICY='{
    "rules": [
        {
            "rulePriority": 1,
            "description": "태그 없는 이미지 30일 후 자동 삭제",
            "selection": {
                "tagStatus": "untagged",
                "countType": "sinceImagePushed",
                "countUnit": "days",
                "countNumber": 30
            },
            "action": {"type": "expire"}
        },
        {
            "rulePriority": 2,
            "description": "태그된 이미지 최대 30개 보관",
            "selection": {
                "tagStatus": "tagged",
                "tagPrefixList": ["sha-", "v"],
                "countType": "imageCountMoreThan",
                "countNumber": 30
            },
            "action": {"type": "expire"}
        }
    ]
}'

# ── 리포지토리 생성 함수 ───────────────────────────────────────────────────
create_ecr_repo() {
    local REPO_NAME="$1"
    echo ""
    echo "[ECR Setup] === 리포지토리 생성 중: ${REPO_NAME} ==="

    # 이미 존재하는 경우 스킵
    if aws ecr describe-repositories \
        --repository-names "${REPO_NAME}" \
        --region "${AWS_REGION}" \
        --output text > /dev/null 2>&1; then
        echo "[ECR Setup] ⚠️  이미 존재하는 리포지토리입니다. 스킵합니다: ${REPO_NAME}"
    else
        # 리포지토리 생성 (이미지 스캔 자동 활성화, 태그 불변성 비활성화)
        aws ecr create-repository \
            --repository-name "${REPO_NAME}" \
            --region "${AWS_REGION}" \
            --image-scanning-configuration scanOnPush=true \
            --image-tag-mutability MUTABLE \
            --output table
        echo "[ECR Setup] ✅ 리포지토리 생성 완료: ${REPO_NAME}"
    fi

    # 라이프사이클 정책 적용 (존재 여부와 관계없이 항상 덮어쓰기)
    aws ecr put-lifecycle-policy \
        --repository-name "${REPO_NAME}" \
        --region "${AWS_REGION}" \
        --lifecycle-policy-text "${LIFECYCLE_POLICY}" \
        --output table
    echo "[ECR Setup] ✅ 라이프사이클 정책 적용: ${REPO_NAME}"

    # 최종 리포지토리 URI 출력
    REPO_URI=$(aws ecr describe-repositories \
        --repository-names "${REPO_NAME}" \
        --region "${AWS_REGION}" \
        --query 'repositories[0].repositoryUri' \
        --output text)
    echo "[ECR Setup] 📦 리포지토리 URI: ${REPO_URI}"
}

# ── 실행 ───────────────────────────────────────────────────────────────────
create_ecr_repo "${REPO_STAGING}"
create_ecr_repo "${REPO_PROD}"

# ── OIDC Provider 생성 안내 ────────────────────────────────────────────────
echo ""
echo "========================================================================"
echo "[ECR Setup] ✅ ECR 리포지토리 생성 완료!"
echo ""
echo "다음 단계: GitHub Actions OIDC IAM 역할 생성"
echo "아래 명령어를 순서대로 실행하세요."
echo "========================================================================"
echo ""
echo "# 1. OIDC Provider 생성 (계정당 1회만 필요)"
echo "aws iam create-open-id-connect-provider \\"
echo "  --url https://token.actions.githubusercontent.com \\"
echo "  --client-id-list sts.amazonaws.com \\"
echo "  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1"
echo ""
echo "# 2. Trust Policy 파일 생성 – <ORG>/<REPO> 를 실제 값으로 교체"
echo "cat > /tmp/github-trust.json << 'EOF'"
echo '{'
echo '  "Version": "2012-10-17",'
echo '  "Statement": [{'
echo '    "Effect": "Allow",'
echo '    "Principal": {"Federated": "arn:aws:iam::263636208782:oidc-provider/token.actions.githubusercontent.com"},'
echo '    "Action": "sts:AssumeRoleWithWebIdentity",'
echo '    "Condition": {'
echo '      "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},'
echo '      "StringLike": {"token.actions.githubusercontent.com:sub": "repo:gksshing/SKN22-4th-2Team:ref:refs/heads/*"}'
echo '    }'
echo '  }]'
echo '}'
echo "EOF"
echo ""
echo "# 3. IAM 역할 생성"
echo "aws iam create-role \\"
echo "  --role-name github-actions-ecr-role \\"
echo "  --assume-role-policy-document file:///tmp/github-trust.json"
echo ""
echo "# 4. 인라인 정책 부착"
echo "aws iam put-role-policy \\"
echo "  --role-name github-actions-ecr-role \\"
echo "  --policy-name GithubActionsECRPolicy \\"
echo "  --policy-document file://infra/iam/github-actions-oidc-policy.json"
echo ""
echo "========================================================================"
