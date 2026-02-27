"""
쇼특허(Short-Cut) – Secrets Manager 유틸리티
=============================================
실행 환경(APP_ENV)에 따라 시크릿 주입 방식을 분기합니다.

  APP_ENV=local       →  .env 파일 로드 (dotenv)
  APP_ENV=production  →  AWS Secrets Manager 호출 → os.environ 주입

우선순위: AWS Secrets Manager > .env > 기존 환경 변수
  - 프로덕션에서는 Secrets Manager 값이 기존 값을 덮어씁니다.
  - 로컬에서는 .env 값이 기존 환경 변수를 덮어씁니다(force=True).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional, Dict

logger = logging.getLogger(__name__)


# =============================================================================
# AWS Secrets Manager 로더
# =============================================================================

def _load_from_secrets_manager(
    secret_name: str,
    region: str,
) -> Dict[str, str]:
    """
    AWS Secrets Manager에서 단일 시크릿을 읽어 키-값 딕셔너리로 반환합니다.

    Args:
        secret_name: Secrets Manager 시크릿 이름 (예: short-cut/prod/app)
        region:      AWS 리전 (예: us-east-1)

    Returns:
        시크릿 키-값 딕셔너리

    Raises:
        ImportError:  boto3가 설치되지 않은 경우
        ClientError:  Secrets Manager 접근 실패 시
        ValueError:   시크릿 값이 JSON 형식이 아닌 경우
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError as exc:
        raise ImportError(
            "boto3가 설치되어 있지 않습니다. `pip install boto3` 후 다시 시도하세요."
        ) from exc

    client = boto3.client("secretsmanager", region_name=region)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        logger.info("Secrets Manager에서 시크릿 로드 성공: %s", secret_name)
    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        logger.error(
            "Secrets Manager 접근 실패 (secret=%s, code=%s): %s",
            secret_name,
            error_code,
            exc,
        )
        raise

    secret_string: Optional[str] = response.get("SecretString")
    if not secret_string:
        raise ValueError(
            f"시크릿 '{secret_name}'의 값이 비어 있거나 BinarySecret 형식입니다. "
            "JSON 문자열 형식의 SecretString만 지원합니다."
        )

    try:
        return json.loads(secret_string)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"시크릿 '{secret_name}'의 값이 유효한 JSON이 아닙니다: {exc}"
        ) from exc


def _inject_secrets_to_env(secrets: Dict[str, str]) -> None:
    """
    시크릿 딕셔너리를 os.environ에 주입합니다.
    우선순위: Secrets Manager 값이 기존 환경 변수를 덮어씁니다.

    Args:
        secrets: 주입할 키-값 딕셔너리
    """
    for key, value in secrets.items():
        if not isinstance(value, str):
            # 숫자·불리언 등 비문자열 값을 문자열로 변환
            value = str(value)
        old = os.environ.get(key)
        os.environ[key] = value
        if old and old != value:
            logger.debug("환경 변수 덮어쓰기: %s (기존값 존재)", key)
        else:
            logger.debug("환경 변수 주입: %s", key)

    logger.info("%d개 시크릿 환경 변수 주입 완료", len(secrets))


# =============================================================================
# 로컬 .env 로더
# =============================================================================

def _load_from_dotenv(dotenv_path: Optional[str] = None) -> None:
    """
    .env 파일을 읽어 환경 변수로 로드합니다.
    Secrets Manager에서 이미 주입된 값을 override합니다 (override=True).

    단, 프로덕션 환경에서는 이 함수를 호출하지 않습니다.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.warning(
            "python-dotenv가 설치되어 있지 않습니다. .env 로드를 건너뜁니다."
        )
        return

    load_dotenv(dotenv_path=dotenv_path, override=True)


# =============================================================================
# GCP 자격증명 처리
# =============================================================================

def _handle_gcp_credentials() -> None:
    """
    GOOGLE_APPLICATION_CREDENTIALS_JSON 환경 변수가 설정된 경우,
    JSON 내용을 임시 파일로 저장하고 GOOGLE_APPLICATION_CREDENTIALS를 설정합니다.

    GCP SDK는 GOOGLE_APPLICATION_CREDENTIALS 경로를 참조하므로
    JSON 문자열을 직접 읽지 못하는 SDK를 위한 호환 처리입니다.
    """
    credentials_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not credentials_json:
        return

    import tempfile
    import atexit

    try:
        # 임시 파일에 GCP 자격증명 JSON을 기록합니다.
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix="gcp_creds_",
            delete=False,
            encoding="utf-8",
        )
        tmp.write(credentials_json)
        tmp.flush()
        tmp.close()
        os.chmod(tmp.name, 0o600)

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
        logger.info(
            "GCP 자격증명 임시 파일 생성 및 GOOGLE_APPLICATION_CREDENTIALS 설정 완료: %s",
            tmp.name,
        )

        # 프로세스 종료 시 임시 파일 삭제
        def _cleanup_tmp_cred(path: str) -> None:
            try:
                os.remove(path)
                logger.debug("GCP 자격증명 임시 파일 삭제 완료: %s", path)
            except OSError:
                pass

        atexit.register(_cleanup_tmp_cred, tmp.name)

    except OSError as exc:
        logger.error("GCP 자격증명 임시 파일 생성 실패: %s", exc)
        raise


# =============================================================================
# 부트스트랩 진입점
# =============================================================================

def bootstrap_secrets(
    secret_name: str = "short-cut/prod/app",
    aws_region: Optional[str] = None,
) -> None:
    """
    APP_ENV 환경 변수에 따라 시크릿 주입 방식을 선택합니다.

    우선순위 규칙:
      - production:  Secrets Manager → os.environ (override)
                     .env 파일을 사용하지 않습니다.
      - local:       .env 파일 → os.environ (override)
                     boto3 호출 없음.

    Args:
        secret_name: Secrets Manager 시크릿 이름. 환경 변수 SECRET_NAME으로 재정의 가능.
        aws_region:  AWS 리전. 환경 변수 AWS_REGION으로 재정의 가능.
    """
    app_env = os.getenv("APP_ENV", "local").strip().lower()

    # 환경 변수로 재정의 허용 (컨테이너 실행 시 유연성 확보)
    secret_name = os.getenv("SECRET_NAME", secret_name)
    region = aws_region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")

    logger.info("시크릿 부트스트랩 시작 (APP_ENV=%s, REGION=%s)", app_env, region or "default")

    # 1. First, try to load .env if it exists (for local overrides)
    _load_from_dotenv()

    # 2. Then, load from AWS Secrets Manager if in production OR if explicitly requested via SECRET_NAME
    if app_env == "production" or os.getenv("SECRET_NAME"):
        try:
            secrets = _load_from_secrets_manager(secret_name, region)
            _inject_secrets_to_env(secrets)
            _handle_gcp_credentials()
        except Exception as e:
            if app_env == "production":
                # In production, this is a fatal error
                raise
            else:
                # In non-production, just log and continue (maybe env vars are set manually)
                logger.warning("AWS Secrets Manager 로드 실패 (로컬 환경이므로 무시): %s", e)

    # 3. Handle GCP credentials if set manually via env
    if app_env != "production":
        _handle_gcp_credentials()

    logger.info("시크릿 부트스트랩 완료 (APP_ENV=%s)", app_env)
