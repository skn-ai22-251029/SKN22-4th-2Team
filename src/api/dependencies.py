import logging
from fastapi import Request
from src.patent_agent import PatentAgent
from src.history_manager import HistoryManager

logger = logging.getLogger(__name__)

# 싱글턴 인스턴스 재사용
_patent_agent = None
_history_manager = None

def get_patent_agent() -> PatentAgent:
    global _patent_agent
    if _patent_agent is None:
        logger.info("Initializing PatentAgent instance...")
        try:
            _patent_agent = PatentAgent()
            logger.info("PatentAgent initialized successfully.")
        except Exception as e:
            logger.error(
                f"PatentAgent 초기화 실패: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise
    return _patent_agent

def get_history_manager() -> HistoryManager:
    global _history_manager
    if _history_manager is None:
        logger.info("Initializing HistoryManager instance...")
        _history_manager = HistoryManager()
    return _history_manager

