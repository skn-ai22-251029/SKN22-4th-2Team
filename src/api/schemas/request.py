from pydantic import BaseModel, Field
from typing import Optional

class AnalyzeRequest(BaseModel):
    user_idea: str = Field(..., description="사용자의 특허 아이디어", min_length=10)
    use_hybrid: bool = Field(default=True, description="하이브리드 검색 사용 여부")
    stream: bool = Field(default=True, description="스트리밍 응답 여부 (SSE)")
    user_id: str = Field(default="anonymous", description="요청 사용자 ID")
