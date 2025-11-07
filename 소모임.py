import streamlit as st
import sqlite3
from datetime import datetime, date
import os, base64
from dotenv import load_dotenv
load_dotenv()
st.set_page_config(page_title="Journal Club Archiving", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: "Noto Sans KR", "Apple SD Gothic Neo", sans-serif;
}
div[data-testid="stVerticalBlock"] {
    padding-top: 1rem;
    padding-bottom: 1rem;
}
img {
    border-radius: 50%;
}
</style>
""", unsafe_allow_html=True)
ADMIN_PASSWORD = os.getenv("ARCHIVE_PASSWORD")

if not ADMIN_PASSWORD:
    st.error("환경 변수 ARCHIVE_PASSWORD가 설정되어 있지 않습니다. .env 파일을 확인하세요.")
from streamlit_pdf_viewer import pdf_viewer
# =========================
# 🎨 [수정됨] CSS 스타일 주입 (버튼 모서리 수정)
# =========================
st.markdown("""
<style>
/* Streamlit의 기본 버튼 클래스를 타겟팅합니다 */
div.stButton > button:first-child {
    background-color: #f0f8ff; /* 요청하신 배경색 */
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    color: #333;               
    /* ⭐️ [수정] 하단 모서리만 둥글게 */
    border-radius: 0 0 5px 5px; 
    margin-bottom: 10px; /* 카드 간 여백 추가 */
}

/* ⭐️ [수정] 포커스 상태 */
div.stButton > button:first-child:focus {
    background-color: #e0f0ff; 
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    border-radius: 0 0 5px 5px; /* ⭐️ 수정 */
}

/* ⭐️ [수정] 호버 상태 */
div.stButton > button:first-child:hover {
    background-color: #e0f0ff; 
    color: #111;
    border: none !important;
    outline: none !important;
    border-radius: 0 0 5px 5px; /* ⭐️ 수정 */
}

/* ⭐️ [수정] 클릭 상태 */
div.stButton > button:first-child:active {
    background-color: #d0e0ff; 
    color: #000;
    border: none !important;
    outline: none !important;
    border-radius: 0 0 5px 5px; /* ⭐️ 수정 */
}

/* ⭐️ [추가됨] 플로팅 홈 버튼 스타일 */
.floating-home-btn {
    position: fixed;
    width: 60px;  /* 원형 버튼 크기 */
    height: 60px; /* 원형 버튼 크기 */
    bottom: 30px; /* 화면 하단에서 30px */
    right: 30px;  /* 화면 우측에서 30px */
    background-color: #f0f8ff; /* 기존 버튼과 톤 통일 */
    color: #333; /* 아이콘 색상 */
    border-radius: 50%; /* 원형 */
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 30px; /* 이모지 아이콘 크기 */
    text-decoration: none;
    box-shadow: 0 4px 10px rgba(0,0,0,0.15); /* 그림자 */
    z-index: 9999; /* 다른 요소들 위에 표시 */
    border: 1px solid #ddd; /* 옅은 테두리 */
    cursor: pointer;
}

.floating-home-btn:hover {
    background-color: #e0f0ff; /* 기존 버튼 호버와 통일 */
    color: #111;
}
</style>
""", unsafe_allow_html=True)


# =========================
# DB 설정
# =========================
conn = sqlite3.connect("meeting_archive.db")
c = conn.cursor()

# 기존 테이블 생성
c.execute("""CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE
            )""")

c.execute("""CREATE TABLE IF NOT EXISTS comments (
                meeting_id INTEGER,
                person TEXT,
                comment TEXT,
                timestamp TEXT
            )""")

# ⭐️ [추가] links 테이블 생성
c.execute("""CREATE TABLE IF NOT EXISTS links (
                meeting_id INTEGER,
                person TEXT,
                link TEXT,
                PRIMARY KEY (meeting_id, person)
            )""")
conn.commit()
# =========================
# 링크 관련 함수
# =========================
def get_link(meeting_id, person):
    c.execute("SELECT link FROM links WHERE meeting_id=? AND person=?", (meeting_id, person))
    row = c.fetchone()
    return row[0] if row else ""

def set_link(meeting_id, person, link):
    # upsert
    c.execute(
        "INSERT INTO links (meeting_id, person, link) VALUES (?, ?, ?) ON CONFLICT(meeting_id, person) DO UPDATE SET link=excluded.link",
        (meeting_id, person, link)
    )
    conn.commit()

# =========================
# 유틸 함수
# =========================
# ⭐️ [수정됨] show_pdf 함수
def show_pdf(file_path):
    """PDF 파일 미리보기 (streamlit-pdf-viewer 사용)"""
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()
    
    # ⭐️ pdf_viewer 라이브러리 사용
    pdf_viewer(pdf_bytes, height=900)
def add_comment(meeting_id, person, comment):
    c.execute(
        "INSERT INTO comments VALUES (?, ?, ?, ?)",
        (meeting_id, person, comment, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()

def get_comments(meeting_id, person):
    c.execute("SELECT person, comment, timestamp FROM comments WHERE meeting_id=? AND person=?", (meeting_id, person))
    return c.fetchall()

def get_base64_image(file_path):
    """파일 경로를 받아 Base64로 인코딩된 이미지 문자열 반환"""
    try:
        with open(file_path, "rb") as img_file:
            encoded_string = base64.b64encode(img_file.read()).decode("utf-8")
        return encoded_string
    except FileNotFoundError:
        st.error(f"이미지 파일을 찾을 수 없습니다: {file_path}")
        return "" # 오류 발생 시 빈 문자열 반환

# ⭐️ 새로운 함수: 댓글 삭제
def delete_comment(meeting_id, person, timestamp):
    c.execute("DELETE FROM comments WHERE meeting_id=? AND person=? AND timestamp=?", (meeting_id, person, timestamp))
    conn.commit()

# =========================
# 사이드바
# =========================
with st.sidebar:
    st.markdown("## 📚 소모임 자료실 📚")
    st.write("명지대학교 문헌정보학과 소속 논문 리딩 소모임의 아카이빙 페이지 입니다. 모임에 사용한 발표자료와 토의 내용을 아카이빙 합니다.")
    st.markdown("---")

    st.markdown("### 📅 모임 일정 관리")

    # --- 일정 추가 ---
    new_date = st.date_input("새 모임 날짜 선택")

    # 비밀번호 입력 필드 (초기에는 숨김)
    if "show_pwd" not in st.session_state:
        st.session_state.show_pwd = False

    if st.button("일정 추가하기"):
        st.session_state.show_pwd = True

    if st.session_state.show_pwd:
        pwd = st.text_input("일정을 추가하려면 비밀번호를 입력하세요", type="password", key="add_pwd")
        if st.button("확인"):
            if pwd == ADMIN_PASSWORD:  # 환경 변수 비밀번호 사용
                try:
                    c.execute("INSERT INTO meetings (date) VALUES (?)", (str(new_date),))
                    conn.commit()
                    st.success(f"{new_date} 일정이 추가되었습니다.")
                    st.session_state.show_pwd = False
                except sqlite3.IntegrityError:
                    st.warning("이미 존재하는 일정입니다.")
            else:
                st.error("비밀번호가 올바르지 않습니다.")

    st.markdown("---")
    st.markdown("### 📂 모임 기록")

    # 일정 목록 불러오기
    c.execute("SELECT id, date FROM meetings ORDER BY date ASC")
    meetings = c.fetchall()

    # 현재 선택된 일정
    if "selected_meeting" not in st.session_state:
        st.session_state.selected_meeting = None
    if "selected_person" not in st.session_state:
        st.session_state.selected_person = None

    if meetings:
        for m_id, m_date in meetings:
            if st.button(f"📅 {m_date}", key=f"meeting_{m_id}"):
                st.session_state.selected_meeting = (m_id, m_date)
                st.session_state.selected_person = None
    else:
        st.info("등록된 일정이 없습니다.")

# =========================
# 메인 화면
# =========================

# =========================
# 배너 이미지 삽입 (title.png, 중앙 정렬, 고정 크기)
# =========================
banner_path = "title.png"
banner_base64 = get_base64_image(banner_path)
if banner_base64:
    st.markdown(
        f'''
        <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{banner_base64}" style="max-width: 90%; height: auto; object-fit: contain; display: block; margin: 0 auto;"/>
        </div>
        ''', unsafe_allow_html=True
    )

if st.session_state.selected_meeting:
    meeting_id, meeting_date = st.session_state.selected_meeting

    # ⭐️ [추가됨] 플로팅 홈 버튼 렌더링
    st.markdown(
        """
        <a href="/" target="_self" class="floating-home-btn">
            🏠
        </a>
        """,
        unsafe_allow_html=True
    )

    people = ["박도현", "박세진", "박형민", "심유현"]

    # 각 인물별 이미지 파일 매핑
    person_img_map = {
        "박도현": "나메코도현.png",
        "박세진": "나메코세진.png",
        "박형민": "나메코형민.png",
        "심유현": "나메코유현.png"
    }

    # ⭐️ [수정됨] 인물 선택: HTML로 이미지 배경 박스 생성
    if st.session_state.selected_person is None:
        st.header(f"📅 {meeting_date} 모임")

        cols = st.columns(2)
        for idx, person in enumerate(people):
            col = cols[idx % 2]
            with col:
                # 인물별 이미지 경로 선택
                img_path = person_img_map.get(person, "")
                img_base64 = get_base64_image(img_path) if img_path else ""

                st.markdown(f"""
                <div style="
                    background-color: #f0f8ff; 
                    padding: 20px; 
                    border-radius: 10px 10px 0 0; 
                    display: flex; 
                    justify-content: center; 
                    align-items: center; 
                    min-height: 160px;
                ">
                    <img src="data:image/png;base64,{img_base64}" 
                        style="
                            width: 120px; 
                            height: 120px; 
                            object-fit: cover; 
                            border-radius: 50%;
                        ">
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(person, key=f"btn_{person}", use_container_width=True):
                    
                    current_meeting = st.session_state.selected_meeting
                    st.session_state.selected_person = person
                    st.session_state.selected_meeting = current_meeting 
                    
                    st.rerun() # ⭐️ 페이지 이동을 위한 것이므로 유지
    
    # --- 인물 선택 후 상세 페이지 ---
    else:
        person = st.session_state.selected_person
        st.header(f"📅 {meeting_date} 모임 - {person}")

        folder = f"uploads/{meeting_date}/{person}"
        os.makedirs(folder, exist_ok=True)


        # =========================
        # ⭐️ [수정됨] 원문 링크 표시 및 수정 UI
        # =========================
        st.markdown("---")
        st.subheader("🔗 원문 바로가기")
        current_link = get_link(meeting_id, person)

        # 링크 수정 관련 상태 관리 (먼저 정의)
        link_edit_key = f"link_edit_mode_{meeting_id}_{person}"
        link_pwd_key = f"link_pwd_{meeting_id}_{person}"
        link_input_key = f"link_input_{meeting_id}_{person}"
        link_pwd_show_key = f"link_pwd_show_{meeting_id}_{person}"
        link_save_msg_key = f"link_save_msg_{meeting_id}_{person}"
        # 상태 초기화
        if link_edit_key not in st.session_state:
            st.session_state[link_edit_key] = False
        if link_pwd_show_key not in st.session_state:
            st.session_state[link_pwd_show_key] = False
        if link_save_msg_key not in st.session_state:
            st.session_state[link_save_msg_key] = ""

        # --- ⭐️ 링크 블럭과 수정 버튼을 st.columns로 묶기 ---
        link_block_cols = st.columns([10, 1]) # [Block, Button]

        with link_block_cols[0]:
            link_display_text = ""
            if current_link:
                link_display_text = f" <a href='{current_link}' target='_blank' style='color: #00008B; word-break: break-all;'>{current_link}</a>"
            else:
                link_display_text = "아직 저장된 원문 링크가 없습니다."

            st.markdown(
                f"""
                <div style="
                    background-color: #f0f8ff; 
                    padding: 1rem;
                    border-radius: 0.5rem;
                    border: 1px solid #e0e0e0; /* 옅은 테두리 */
                    min-height: 55px; /* 버튼과 최소 높이 맞춤 */
                    display: flex;
                    align-items: center; /* 세로 중앙 정렬 */
                ">
                    <span style="font-family: 'sans serif'; font-size: 14px; color: #31333F;">
                        {link_display_text}
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

        with link_block_cols[1]:
            st.markdown(
                """
                <div style="display: flex; align-items: center; justify-content: center; height: 100%;">
                """,
                unsafe_allow_html=True
            )
            if st.button("✏️", key=f"edit_link_btn_{meeting_id}_{person}", help="원문 링크 수정"):
                st.session_state[link_pwd_show_key] = True
                st.session_state[link_edit_key] = False
                st.session_state[link_save_msg_key] = ""
                # ⭐️ [삭제됨] st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)
        
        # --- [이하 수정 로직] ---
        
        # 비밀번호 입력창 표시
        if st.session_state[link_pwd_show_key]:
            pwd = st.text_input("비밀번호 입력", type="password", key=link_pwd_key)
            if st.button("비밀번호 확인", key=f"check_link_pwd_{meeting_id}_{person}"):
                if pwd == ADMIN_PASSWORD:
                    st.session_state[link_edit_key] = True
                    st.session_state[link_pwd_show_key] = False
                    st.session_state[link_save_msg_key] = ""
                    # ⭐️ [삭제됨] st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다.")
        
        # 링크 입력 및 저장
        if st.session_state[link_edit_key]:
            new_link = st.text_input("원문 링크 입력", value=current_link, key=link_input_key)
            if st.button("링크 저장", key=f"save_link_{meeting_id}_{person}"):
                set_link(meeting_id, person, new_link.strip())
                st.session_state[link_edit_key] = False
                st.session_state[link_save_msg_key] = "링크가 저장되었습니다."
                # ⭐️ [삭제됨] st.rerun()

        # 성공 메시지를 1회만 표시하도록 수정
        if st.session_state[link_save_msg_key]:
            st.success(st.session_state[link_save_msg_key])
            st.session_state[link_save_msg_key] = ""


        # =========================
        # ⭐️ PDF 뷰어 로직 (수정 없음, 단지 문제 원인 파악용)
        # =========================
        pdfs = [f for f in os.listdir(folder) if f.endswith(".pdf")]
        
        pdf_session_key = f"pdf_path_{meeting_date}_{person}" 

        pdf_to_show = None
        
        if pdf_session_key in st.session_state:
            pdf_to_show = st.session_state[pdf_session_key]
            if not os.path.exists(pdf_to_show):
                pdf_to_show = None
                del st.session_state[pdf_session_key] 
        
        if pdf_to_show is None and pdfs:
            # ⭐️ 여기가 새로고침 시 문제의 지점: pdfs[0]이 옛날 파일일 수 있음
            pdf_to_show = os.path.join(folder, pdfs[0])
            st.session_state[pdf_session_key] = pdf_to_show 

        if pdf_to_show:
            show_pdf(pdf_to_show) 
        else:
            st.info("아직 업로드된 PDF 파일이 없습니다. 하단에서 업로드해주세요.")


        # =========================
        # 전체 대화
        # =========================
        st.markdown("---")
        st.subheader("💬 논문에 대한 의견 나누기")
        comments = get_comments(meeting_id, person)
        if comments:
            for p, com, t in comments:
                cols = st.columns([10,1])
                with cols[0]:
                    st.markdown(f"🕒 `{t}`  {com}")
                with cols[1]:
                    if st.button("❌", key=f"del_{t}"):
                        st.session_state["delete_target"] = {"timestamp": t, "person": p}
                        st.rerun() # ⭐️ 댓글 삭제 UI 전환을 위해 유지
        else:
            st.info("아직 등록된 대화가 없습니다.")

        # ⭐️ 댓글 삭제 처리 (이 부분의 rerun은 정상 작동을 위해 필요하므로 유지)
        if "delete_target" in st.session_state:
            target = st.session_state["delete_target"]
            st.markdown("---")
            st.warning(f"댓글 삭제를 위해 비밀번호를 입력하세요.\n삭제 대상: {target['person']}님, 시간: {target['timestamp']}")
            del_pwd = st.text_input("비밀번호 입력", type="password", key="del_pwd")
            if st.button("댓글 삭제 확인"):
                if del_pwd == ADMIN_PASSWORD:
                    delete_comment(meeting_id, target["person"], target["timestamp"])
                    st.success("댓글이 삭제되었습니다.")
                    del st.session_state["delete_target"]
                    if "del_pwd" in st.session_state:
                        del st.session_state["del_pwd"]
                    st.rerun() # ⭐️ 삭제 완료 후 UI 복원을 위해 유지
                else:
                    st.error("비밀번호가 올바르지 않습니다.")
            if st.button("삭제 취소"):
                del st.session_state["delete_target"]
                if "del_pwd" in st.session_state:
                    del st.session_state["del_pwd"]
                st.rerun() # ⭐️ 취소 후 UI 복원을 위해 유지

        # =========================
        # 댓글 입력 및 저장 기능
        # =========================
        comment_key = f"comment_{meeting_date}_{person}"
        comment_text = st.text_input(f"{person}님의 자료에 코멘트 남기기", key=comment_key)
        if st.button(f"댓글 저장", key=f"save_{meeting_date}"):
            if comment_text.strip():
                add_comment(meeting_id, person, comment_text)
                st.success("댓글이 저장되었습니다.")
                # ⭐️ [삭제됨] st.rerun() (자동 rerun으로 목록이 갱신됨)
            else:
                st.warning("댓글을 입력해주세요.")

        
        # =========================
        # ⭐️ [수정됨] PDF 업로드 로직
        # =========================
        pwd_key = f"upload_pwd_{meeting_date}_{person}"
        upload_ready_key = f"upload_ready_{meeting_date}_{person}"
        if upload_ready_key not in st.session_state:
            st.session_state[upload_ready_key] = False

        def reset_upload_ready():
            st.session_state[upload_ready_key] = False

        st.markdown("---")
        st.subheader("📝 pdf 파일 관리")
        if not st.session_state[upload_ready_key]:
            pwd = st.text_input(
                "PDF 수정을 위해 비밀번호를 입력하세요",
                type="password",
                key=pwd_key,
                on_change=reset_upload_ready,
            )
            if st.button("비밀번호 확인", key=f"check_upload_pwd_{meeting_date}_{person}"):
                if pwd == ADMIN_PASSWORD:
                    st.session_state[upload_ready_key] = True
                    st.success("비밀번호가 확인되었습니다. PDF 파일을 업로드하세요.")
                    # ⭐️ [삭제됨] st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다. PDF를 업로드할 수 없습니다.")
        if st.session_state[upload_ready_key]:
            uploaded_file = st.file_uploader(
                f"{person}의 PDF 업로드",
                type=["pdf"],
                key=f"{meeting_date}_{person}",
            )
            if uploaded_file:
                file_path = os.path.join(folder, uploaded_file.name)

                # ⭐️ [수정] 파일 저장 전, 폴더 내의 모든 .pdf 파일을 삭제합니다.
                for f in os.listdir(folder):
                    if f.endswith(".pdf"):
                        os.remove(os.path.join(folder, f))
                
                # 새 파일 저장
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"{person}의 PDF 업로드 완료")
                
                pdf_session_key = f"pdf_path_{meeting_date}_{person}" 
                st.session_state[pdf_session_key] = file_path
                
                # ⭐️ [삭제됨] st.rerun() (파일 업로드 시 자동 rerun됨)

# --- 메인 홈페이지 ---
else:
    # ⭐️ [수정됨] 인물 소개 블록 (윤곽선/그림자 제거, 배경색 통일)
    st.markdown("##  소모임 멤버 소개")
    people = [
        {
            "name": "박도현",
            "major": "명지대학교 문헌정보학과 4학년",
            "photo_path": "나메코도현.png",
            "intro": "저는 명지대학교 문헌정보학과 4학년에 재학중이며, 텍스트마이닝과 항공 분야에 관심이 많습니다.",
        },
        {
            "name": "박세진",
            "major": "명지대학교 일반 대학원 문헌정보학과 석사 2차",
            "photo_path": "나메코세진.png",
            "intro": "아직 소개글이 없습니다.",
        },
        {
            "name": "박형민",
            "major": "명지대학교 문헌정보학과 4학년",
            "photo_path": "나메코형민.png",
            "intro": "아직 소개글이 없습니다.",
        },
        {
            "name": "심유현",
            "major": "명지대학교 문헌정보학과 4학년",
            "photo_path": "나메코유현.png",
            "intro": "아직 소개글이 없습니다.",
        },
    ]

    st.markdown("<div style='max-width: 900px; margin: auto;'>", unsafe_allow_html=True)
    for person in people:
        img_base64 = get_base64_image(person["photo_path"])
        if img_base64: 
            st.markdown(
                f"""
                <div style="
                    background-color: #f0f8ff;  /* 배경색 통일 */
                    padding: 25px;
                    margin-bottom: 15px;
                    box-shadow: none;           /* 그림자 제거 */
                    border-radius: 10px;
                    border: none;               /* 윤곽선 제거 */
                ">
                    <div style="display: flex; align-items: center;">
                        <img src="data:image/png;base64,{img_base64}" style="width: 80px; height: 80px; object-fit: cover; border-radius: 50%; margin-right: 15px;" />
                        <div>
                            <h3 style="margin: 0;">{person['name']}</h3>
                            <h5 style="margin: 0;">{person['major']}</h5>
                            <p style="margin: 5px 0 0 0;">{person['intro']}</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
