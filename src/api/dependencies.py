import logging
from fastapi import Request
from src.patent_agent import PatentAgent
from src.history_manager import HistoryManager

logger = logging.getLogger(__name__)

# Singletons for reusing instances across requests
_patent_agent = None
_history_manager = None

def get_patent_agent() -> PatentAgent:
    global _patent_agent
    if _patent_agent is None:
        logger.info("Initializing PatentAgent instance...")
        _patent_agent = PatentAgent()
    return _patent_agent

def get_history_manager() -> HistoryManager:
    global _history_manager
    if _history_manager is None:
        logger.info("Initializing HistoryManager instance...")
        _history_manager = HistoryManager()
    return _history_manager
