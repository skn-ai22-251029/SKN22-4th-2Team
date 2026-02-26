import re
import logging
import html
from typing import Optional, List

import os
import json

# 로거 설정
logger = logging.getLogger(__name__)

# 기본 위험 패턴 정의 (Prompt Injection 방어용)
DEFAULT_DANGEROUS_PATTERNS = [
    r"(?:ignore|disregard)\s+(?:the\s+)?(?:above|previous|below|system|instruction|prompt)",
    r"you\s+are\s+now\s+a",
    r"new\s+rule",
    r"system\s+override",
    r"don't\s+follow\s+the\s+instructions",
    r"answer\s+as\s+a",
    r"forget\s+everything\s+we\s+talked\s+about",
    r"previous\s+context\s+is\s+deleted",
    r"translated\s+as\s+follow",
]

# 한글 위험 패턴 (공백에 유연하게 대응)
DEFAULT_DANGEROUS_PATTERNS_KO = [
    r"이전\s*지침을?\s*무시",
    r"시스템\s*프롬프트를?\s*무시",
    r"앞의\s*내용은?\s*무시",
    r"지금부터\s*당신은",
    r"새로운\s*규칙",
    r"시스템\s*재설정",
    r"지침을?\s*따르지\s*마세요",
    r"대신\s*답변하세요",
]

def load_dangerous_patterns() -> List[str]:
    """YAML/JSON 설정 파일이나 DB에서 동적으로 로드하는 대신,
    우선 파일 기반으로 로드하도록 구성하여 추후 재배포 없이 유연한 대응이 가능하게 함."""
    patterns = []
    patterns_file = os.getenv("DANGEROUS_PATTERNS_FILE", "dangerous_patterns.json")
    if os.path.exists(patterns_file):
        try:
            with open(patterns_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                patterns.extend(data.get("en", []))
                patterns.extend(data.get("ko", []))
        except Exception as e:
            logger.error(f"Failed to load patterns from {patterns_file}: {e}")
    
    if not patterns:
        patterns = DEFAULT_DANGEROUS_PATTERNS + DEFAULT_DANGEROUS_PATTERNS_KO
    return patterns

# 캐싱된 패턴 리스트 (실제 운영시에는 스케줄러를 통해 주기적 갱신 가능)
ACTIVE_DANGEROUS_PATTERNS = load_dangerous_patterns()

MAX_INPUT_LENGTH = 2000

class PromptInjectionError(ValueError):
    """Prompt Injection 공격이 감지되었을 때 발생하는 예외입니다."""
    pass

def sanitize_user_input(text: str) -> str:
    """
    사용자 입력을 샌드박싱 처리합니다.
    1. 길이 제한 (2,000자)
    2. 위험 패턴 감지 (Prompt Injection)
    3. 마크다운/특수 문자 이스케이핑
    """
    if not text:
        return ""

    # 1. 길이 제한
    if len(text) > MAX_INPUT_LENGTH:
        logger.warning(f"[Security] Input length exceeded: {len(text)}")
        raise PromptInjectionError(f"Input is too long (Max {MAX_INPUT_LENGTH} characters).")

    # 2. 위험 패턴 감지
    detect_injection(text)

    # 3. 마크다운 이스케이핑 및 HTML 이스케이핑
    sanitized = html.escape(text)
    
    return sanitized

def detect_injection(text: str) -> None:
    """
    정규식을 사용하여 프롬프트 인젝션 패턴을 탐지합니다.
    """
    if not text:
        return

    text_lower = text.lower()
    
    for pattern in ACTIVE_DANGEROUS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            masked_text = text[:15] + "..." + text[-15:] if len(text) > 30 else text
            logger.warning(
                f"[Security] Potential Prompt Injection detected!",
                extra={
                    "event": "prompt_injection_detection",
                    "pattern": pattern,
                    "masked_input": masked_text
                }
            )
            raise PromptInjectionError("악의적인 입력 패턴이 감지되었습니다. 정상적인 요청만 입력해주세요.")

def wrap_user_query(text: str) -> str:
    """
    사용자 입력을 <user_query> 태그로 감싸 시스템 프롬프트와 구조적으로 분리합니다.
    """
    return f"<user_query>\n{text}\n</user_query>"
