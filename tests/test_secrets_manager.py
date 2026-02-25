"""
AWS Secrets Manager 유틸리티 유닛 테스트
=========================================
APP_ENV=local  → dotenv 경로 검증
APP_ENV=production → boto3 mock 경로 검증
ClientError 발생 시 예외 전파 검증
"""

from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch, call


class TestBootstrapSecretsLocal(unittest.TestCase):
    """APP_ENV=local 일 때 .env 파일 로드 경로 테스트"""

    def setUp(self) -> None:
        # 각 테스트 전에 APP_ENV를 초기화합니다.
        os.environ.pop("APP_ENV", None)

    @patch("src.secrets_manager._load_from_dotenv")
    def test_local_calls_dotenv(self, mock_dotenv: MagicMock) -> None:
        """APP_ENV=local(기본값)일 때 _load_from_dotenv가 호출되어야 합니다."""
        os.environ["APP_ENV"] = "local"

        from src.secrets_manager import bootstrap_secrets
        bootstrap_secrets()

        mock_dotenv.assert_called_once()

    @patch("src.secrets_manager._load_from_secrets_manager")
    def test_local_does_not_call_secrets_manager(
        self, mock_sm: MagicMock
    ) -> None:
        """APP_ENV=local일 때 Secrets Manager를 호출하지 않아야 합니다."""
        os.environ["APP_ENV"] = "local"

        from src.secrets_manager import bootstrap_secrets
        bootstrap_secrets()

        mock_sm.assert_not_called()

    @patch("src.secrets_manager._load_from_dotenv")
    def test_default_env_is_local(self, mock_dotenv: MagicMock) -> None:
        """APP_ENV가 없을 때 기본값 'local'로 동작해야 합니다."""
        os.environ.pop("APP_ENV", None)

        from src.secrets_manager import bootstrap_secrets
        bootstrap_secrets()

        mock_dotenv.assert_called_once()


class TestBootstrapSecretsProduction(unittest.TestCase):
    """APP_ENV=production 일 때 Secrets Manager 경로 테스트"""

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["AWS_REGION"] = "us-east-1"
        os.environ["SECRET_NAME"] = "short-cut/prod/app"

    def tearDown(self) -> None:
        for key in ("APP_ENV", "AWS_REGION", "SECRET_NAME"):
            os.environ.pop(key, None)

    @patch("src.secrets_manager._inject_secrets_to_env")
    @patch("src.secrets_manager._load_from_secrets_manager")
    def test_production_calls_secrets_manager(
        self,
        mock_load: MagicMock,
        mock_inject: MagicMock,
    ) -> None:
        """APP_ENV=production일 때 Secrets Manager가 호출되어야 합니다."""
        mock_load.return_value = {"OPENAI_API_KEY": "sk-test"}

        from src.secrets_manager import bootstrap_secrets
        bootstrap_secrets()

        mock_load.assert_called_once_with("short-cut/prod/app", "us-east-1")
        mock_inject.assert_called_once_with({"OPENAI_API_KEY": "sk-test"})

    @patch("src.secrets_manager._load_from_dotenv")
    @patch("src.secrets_manager._inject_secrets_to_env")
    @patch("src.secrets_manager._load_from_secrets_manager")
    def test_production_does_not_call_dotenv(
        self,
        mock_load: MagicMock,
        mock_inject: MagicMock,
        mock_dotenv: MagicMock,
    ) -> None:
        """APP_ENV=production일 때 .env 파일을 로드하지 않아야 합니다."""
        mock_load.return_value = {}

        from src.secrets_manager import bootstrap_secrets
        bootstrap_secrets()

        mock_dotenv.assert_not_called()


class TestLoadFromSecretsManager(unittest.TestCase):
    """_load_from_secrets_manager 함수 테스트"""

    def test_returns_parsed_secret(self) -> None:
        """Secrets Manager 응답 JSON이 올바르게 파싱되어야 합니다."""
        secret_data = {
            "OPENAI_API_KEY": "sk-test-key",
            "PINECONE_API_KEY": "pc-test-key",
        }

        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data)
        }

        with patch("boto3.client", return_value=mock_client):
            from src.secrets_manager import _load_from_secrets_manager
            result = _load_from_secrets_manager("short-cut/prod/app", "us-east-1")

        self.assertEqual(result, secret_data)
        mock_client.get_secret_value.assert_called_once_with(
            SecretId="short-cut/prod/app"
        )

    def test_raises_on_client_error(self) -> None:
        """ClientError 발생 시 예외가 전파되어야 합니다."""
        import boto3
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "not found"}},
            "GetSecretValue",
        )

        with patch("boto3.client", return_value=mock_client):
            from src.secrets_manager import _load_from_secrets_manager
            with self.assertRaises(ClientError):
                _load_from_secrets_manager("nonexistent-secret", "us-east-1")

    def test_raises_on_invalid_json(self) -> None:
        """SecretString이 JSON이 아닌 경우 ValueError가 발생해야 합니다."""
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            "SecretString": "not-valid-json"
        }

        with patch("boto3.client", return_value=mock_client):
            from src.secrets_manager import _load_from_secrets_manager
            with self.assertRaises(ValueError):
                _load_from_secrets_manager("short-cut/prod/app", "us-east-1")


class TestInjectSecretsToEnv(unittest.TestCase):
    """_inject_secrets_to_env 우선순위 테스트"""

    def tearDown(self) -> None:
        # 테스트 후 주입된 환경 변수 정리
        for key in ("TEST_KEY_A", "TEST_KEY_B"):
            os.environ.pop(key, None)

    def test_injects_new_keys(self) -> None:
        """새 키가 os.environ에 추가되어야 합니다."""
        from src.secrets_manager import _inject_secrets_to_env
        _inject_secrets_to_env({"TEST_KEY_A": "value_a"})
        self.assertEqual(os.environ.get("TEST_KEY_A"), "value_a")

    def test_overrides_existing_keys(self) -> None:
        """기존 환경 변수보다 Secrets Manager 값이 우선해야 합니다."""
        os.environ["TEST_KEY_B"] = "old_value"

        from src.secrets_manager import _inject_secrets_to_env
        _inject_secrets_to_env({"TEST_KEY_B": "new_value_from_sm"})

        self.assertEqual(os.environ.get("TEST_KEY_B"), "new_value_from_sm")


if __name__ == "__main__":
    unittest.main()
