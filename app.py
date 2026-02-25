"""
Short-Cut Main Application.
"""
import asyncio
import os
import streamlit as st
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# Streamlit Config (Must be first)
st.set_page_config(
    page_title="Short-Cut",
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded",
)

# API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Imports after page config
from src.session_manager import init_session_state, load_history, save_result_to_history
from src.ui.styles import get_main_css
from src.ui.components import render_header, render_sidebar, render_search_results, render_footer
from src.analysis_logic import run_full_analysis

# Initialize Session
init_session_state()
load_history()

# Apply Global CSS
st.markdown(get_main_css(), unsafe_allow_html=True)

# Render UI
render_header()

# Cached Resource Loading
@st.cache_resource
def load_db_client():
    """Load Pinecone + BM25 hybrid client (optimized for speed)."""
    from src.vector_db import PineconeClient
    try:
        # skip_init_check=True reduces 1-2 seconds of network IO during startup
        client = PineconeClient(skip_init_check=True) 
        return client
    except Exception as e:
        st.error(f"데이터베이스 연결 실패: {e}")
        return None

DB_CLIENT = load_db_client()

# Sidebar (Stats are fetched lazily inside components if needed)
use_hybrid, selected_ipc_codes = render_sidebar(OPENAI_API_KEY, DB_CLIENT)

# Main Content - Input
st.markdown("### 💡 아이디어 입력")
st.caption("특허로 출원하려는 아이디어를 설명해주세요. 유사 특허를 찾아 침해 리스크를 분석합니다.")

user_idea = st.text_area(
    label="아이디어 설명",
    placeholder="예: 딥러닝 기반 문서 요약 시스템으로, 긴 문서를 입력받아 핵심 내용을 추출하고 요약문을 생성합니다...",
    height=120,
    label_visibility="collapsed",
)

# Analysis Check
can_analyze = (
    user_idea and 
    OPENAI_API_KEY and 
    DB_CLIENT
)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    analyze_button = st.button(
        "🔍 특허 분석 시작",
        type="primary",
        use_container_width=True,
        disabled=not can_analyze,
    )

if not can_analyze and user_idea:
    if not OPENAI_API_KEY:
        st.warning("⚠️ OpenAI API 키를 설정하세요.")
    elif not DB_CLIENT:
        st.warning("⚠️ DB 클라이언트 초기화 실패.")

# Analysis Execution
if analyze_button and can_analyze:
    status_container = st.container()
    streaming_container = st.container()
    
    try:
        # Run async analysis natively
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_and_update_ui():
            user_id = st.session_state.get("user_id", "unknown")
            final_res = None
            
            progress_bar = status_container.progress(0, text="🚀 준비 중...")
            status = status_container.status("🔍 특허 분석 시작...", expanded=True)
            
            stream_placeholder = streaming_container.empty()
            full_text = ""
            
            async for event in run_full_analysis(
                user_idea=user_idea,
                user_id=user_id,
                db_client=DB_CLIENT,
                history_manager=st.session_state.history_manager,
                use_hybrid=use_hybrid,
                ipc_filters=selected_ipc_codes
            ):
                if event["type"] == "progress":
                    progress_bar.progress(event["percent"], text=event["message"])
                elif event["type"] == "step_info":
                    status.write(f"**Step {event['step']}**: {event['message']}")
                elif event["type"] == "info":
                    status.write(event["message"])
                elif event["type"] == "queries":
                    with status.expander("생성된 검색 쿼리 보기", expanded=False):
                        for i, q in enumerate(event["data"]):
                            st.write(f"**Q{i+1}**: {q}")
                elif event["type"] == "stream_token":
                    full_text += event["content"]
                    stream_placeholder.markdown(full_text + "▌")
                elif event["type"] == "stream_full":
                    stream_placeholder.markdown(event["content"])
                elif event["type"] == "result":
                    final_res = event["data"]
            
            status.update(label="✅ 분석 완료!", state="complete", expanded=False)
            return final_res
            
        result = loop.run_until_complete(run_and_update_ui())
        
        loop.close()
        
        # Save result
        save_result_to_history(result)
            
    except Exception as e:
        st.error(f"❌ 분석 중 오류가 발생했습니다: {str(e)}")
        st.info("💡 OpenAI API 키를 확인하거나, 잠시 후 다시 시도해주세요.")

# Results Display
if st.session_state.current_result:
    render_search_results(st.session_state.current_result)

# Footer
render_footer()
