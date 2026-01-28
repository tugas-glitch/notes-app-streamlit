import streamlit as st
import sqlite3
import bcrypt
import base64
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Notes App",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# SESSION
# =====================================================
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "all"
if "filter_category" not in st.session_state:
    st.session_state.filter_category = "Semua"
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "show_add" not in st.session_state:
    st.session_state.show_add = False

# =====================================================
# DATABASE (SQLITE - CLOUD SAFE)
# =====================================================
def db():
    return sqlite3.connect("notes.db", check_same_thread=False)

def init_db():
    con = db()
    c = con.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        category TEXT,
        color TEXT,
        content TEXT,
        image TEXT,
        is_favorite INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    con.commit()
    con.close()

init_db()
# =====================================================
# UTIL
# =====================================================
def get_text_color(bg_hex):
    bg_hex = bg_hex.lstrip("#")
    r, g, b = int(bg_hex[0:2],16), int(bg_hex[2:4],16), int(bg_hex[4:6],16)
    brightness = (r*299 + g*587 + b*114) / 1000
    return "#000000" if brightness > 160 else "#ffffff"

def img_to_b64(file):
    if not file:
        return None
    if file.size > 2 * 1024 * 1024:
        st.error("Ukuran gambar maksimal 2MB")
        return None
    return base64.b64encode(file.read()).decode()

# =====================================================
# AUTH FUNCTIONS (SQLITE SAFE)
# =====================================================
def login(username, password):
    if not username or not password:
        return None

    con = db()
    c = con.cursor()
    c.execute(
        "SELECT id, username, password FROM users WHERE username = ?",
        (username,)
    )
    row = c.fetchone()
    con.close()

    if row and bcrypt.checkpw(password.encode(), row[2].encode()):
        return {"id": row[0], "username": row[1]}
    return None


def register(username, password):
    if not username or not password:
        return False, "Username & password wajib diisi"

    con = db()
    c = con.cursor()

    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    if c.fetchone():
        con.close()
        return False, "Username sudah digunakan"

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    c.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (username, hashed)
    )
    con.commit()
    con.close()

    return True, "Registrasi berhasil"


def reset_pw(username, new_password):
    if not username or not new_password:
        return False

    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    con = db()
    c = con.cursor()
    c.execute(
        "UPDATE users SET password = ? WHERE username = ?",
        (hashed, username)
    )
    con.commit()
    con.close()
    return True

# =====================================================
# NOTES (CRUD)
# =====================================================
def get_notes(user_id):
    con = db()
    c = con.cursor()
    c.execute("""
        SELECT id, title, category, color, content, image, is_favorite
        FROM notes
        WHERE user_id = ?
        ORDER BY is_favorite DESC, created_at DESC
    """, (user_id,))
    rows = c.fetchall()
    con.close()

    notes = []
    for r in rows:
        notes.append({
            "id": r[0],
            "title": r[1],
            "category": r[2],
            "color": r[3],
            "content": r[4],
            "image": r[5],
            "is_favorite": r[6]
        })
    return notes

def add_note(user_id, title, category, color, content, image):
    if not title or not content:
        return
    con = db()
    c = con.cursor()
    c.execute("""
        INSERT INTO notes (user_id, title, category, color, content, image)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, title, category, color, content, image))
    con.commit()
    con.close()

def delete_note(note_id):
    con = db()
    c = con.cursor()
    c.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    con.commit()
    con.close()

def toggle_pin(note_id, value):
    con = db()
    c = con.cursor()
    c.execute(
        "UPDATE notes SET is_favorite = ? WHERE id = ?",
        (value, note_id)
    )
    con.commit()
    con.close()

# =====================================================
# PDF EXPORT
# =====================================================
def export_pdf(notes, category):
    if category != "Semua":
        notes = [n for n in notes if n["category"] == category]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    story = [
        Paragraph(f"<b>NOTES - {category}</b>", styles["Title"]),
        Spacer(1, 12)
    ]

    for n in notes:
        story.append(
            Paragraph(
                f"<b>{n['title']}</b><br/>{n['content']}",
                styles["Normal"]
            )
        )
        story.append(Spacer(1, 10))

    doc.build(story)
    buffer.seek(0)
    return buffer
# =====================================================
# CSS - GOOGLE KEEP STYLE + MOBILE FRIENDLY
# =====================================================
st.markdown("""
<style>
/* CARD */
.note-card {
    padding: 16px;
    border-radius: 18px;
    margin-bottom: 16px;
    box-shadow: 0 2px 6px rgba(0,0,0,.15);
    break-inside: avoid;
}
.note-title {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 6px;
}
.note-content {
    font-size: 14px;
    line-height: 1.5;
    white-space: pre-wrap;
}
.note-img {
    margin-top: 10px;
    border-radius: 12px;
    max-width: 100%;
}
.pinned {
    border: 2px solid #f4c430;
}

/* MASONRY LAYOUT */
.masonry {
    column-count: 1;
    column-gap: 16px;
}
@media (min-width: 768px) {
    .masonry { column-count: 3; }
}

/* MOBILE FIX */
@media (max-width: 768px) {
    h1 { font-size: 22px !important; }
    h2 { font-size: 18px !important; }
    button { width: 100% !important; }
}

/* IMAGE FULLSCREEN PREVIEW */
.preview-img { cursor: zoom-in; }
.preview-img:active {
    position: fixed;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    object-fit: contain;
    background: rgba(0,0,0,.95);
    z-index: 9999;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# THEME (LIGHT / DARK MODE - TEXT PUTIH JELAS)
# =====================================================
if st.session_state.dark_mode:
    st.markdown("""
    <style>
    /* ROOT APP */
    .stApp {
        background-color: #121212 !important;
        color: #ffffff !important;
    }

    /* HEADINGS & TEXT (AMAN, TIDAK GLOBAL DIV) */
    h1, h2, h3, h4, h5, h6,
    p, label, span {
        color: #ffffff !important;
    }

    /* MAIN CONTENT WRAPPER */
    section.main {
        background-color: #121212 !important;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #1e1e1e !important;
    }

    /* INPUT & TEXTAREA */
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea {
        background-color: #1f1f1f !important;
        color: #ffffff !important;
        border: 1px solid #444 !important;
        border-radius: 10px !important;
    }

    /* SELECTBOX */
    div[data-baseweb="select"] > div {
        background-color: #1f1f1f !important;
        color: #ffffff !important;
        border: 1px solid #444 !important;
        border-radius: 10px !important;
    }

    /* BUTTON */
    button[data-testid="baseButton-secondary"],
    button[data-testid="baseButton-primary"] {
        background-color: #2a2a2a !important;
        color: #ffffff !important;
        border: 1px solid #444 !important;
        border-radius: 10px !important;
    }

    button:hover {
        background-color: #333333 !important;
    }

    /* TABS (LOGIN / REGISTER / RESET) */
    button[data-baseweb="tab"] {
        color: #aaaaaa !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        border-bottom: 2px solid #ff5252 !important;
    }

    /* FORM CARD */
    div[data-testid="stForm"] {
        background-color: #1c1c1c !important;
        border-radius: 16px;
        padding: 16px;
        border: 1px solid #333;
    }

    /* DOWNLOAD BUTTON */
    a[download] {
        background-color: #2a2a2a !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        padding: 10px 16px;
        text-decoration: none;
    }

    /* BOTTOM NAV */
    .bottom-nav {
        background-color: #1a1a1a !important;
        border-top: 1px solid #333 !important;
    }

    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    .stApp {
        background-color: #ffffff;
        color: #000000;
    }
    </style>
    """, unsafe_allow_html=True)

# =====================================================
# SIDEBAR (SEARCH + FILTER + EXPORT)
# =====================================================
with st.sidebar:
    st.markdown("## 🗂️ Notes")

    st.session_state.search_query = st.text_input(
        "🔍 Cari catatan",
        value=st.session_state.search_query,
        key="sb_search"
    )

    if st.button("📝 Semua Catatan", use_container_width=True):
        st.session_state.view_mode = "all"
    if st.button("⭐ Pinned", use_container_width=True):
        st.session_state.view_mode = "pinned"

    st.markdown("---")
    st.session_state.filter_category = st.selectbox(
        "📂 Kategori",
        ["Semua","Pribadi","Kerja","Kuliah","Ide","Lainnya"],
        key="sb_category"
    )
    if st.session_state.filter_category != "Semua":
        st.session_state.view_mode = "category"

    st.markdown("---")
    if st.session_state.user:
        st.markdown("### 📄 Export PDF")
        st.download_button(
            "⬇️ Download PDF",
            export_pdf(
                get_notes(st.session_state.user["id"]),
                st.session_state.filter_category
            ),
            file_name="notes.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    st.markdown("---")
    st.toggle("🌙 Dark Mode", key="dark_mode")

    if st.session_state.user:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()

# =====================================================
# AUTH PAGE (NO DUPLICATE ELEMENT)
# =====================================================
if not st.session_state.user:
    st.title("📝 Notes App")

    tab1, tab2, tab3 = st.tabs(["🔐 Login", "🆕 Register", "♻️ Reset"])

    # ---------- LOGIN ----------
    with tab1:
        with st.form("login_form"):
            u = st.text_input("Username", key="login_user")
            p = st.text_input("Password", type="password", key="login_pass")
            submit = st.form_submit_button("Login")

            if submit:
                user = login(u, p)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Username / Password salah")

    # ---------- REGISTER ----------
    with tab2:
        with st.form("register_form"):
            ru = st.text_input("Username Baru", key="reg_user")
            rp = st.text_input("Password Baru", type="password", key="reg_pass")
            submit = st.form_submit_button("Register")

            if submit:
                ok, msg = register(ru, rp)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    # ---------- RESET ----------
    with tab3:
        with st.form("reset_form"):
            fu = st.text_input("Username", key="reset_user")
            fp = st.text_input("Password Baru", type="password", key="reset_pass")
            submit = st.form_submit_button("Reset Password")

            if submit:
                reset_pw(fu, fp)
                st.success("Password berhasil direset")

# =====================================================
# MAIN APP
# =====================================================
else:
    st.title("📒 Catatan Saya")

    # ===============================
    # ADD NOTE FORM (ONLY WHEN FAB)
    # ===============================
    if st.session_state.show_add:
        st.markdown("## ➕ Tambah Catatan")

        with st.form("add_note_form"):
            t = st.text_input("Judul")
            cg = st.selectbox(
                "Kategori",
                ["Pribadi","Kerja","Kuliah","Ide","Lainnya"]
            )
            col = st.color_picker("Warna", "#FFF9C4")
            ct = st.text_area("Isi Catatan")
            img = st.file_uploader(
                "Gambar (opsional)",
                type=["png","jpg","jpeg"]
            )

            col1, col2 = st.columns(2)
            with col1:
                save = st.form_submit_button("💾 Simpan")
            with col2:
                cancel = st.form_submit_button("❌ Batal")

            if save:
                add_note(
                    st.session_state.user["id"],
                    t, cg, col, ct, img_to_b64(img)
                )
                st.session_state.show_add = False
                st.rerun()

            if cancel:
                st.session_state.show_add = False
                st.rerun()

    # ===============================
    # LOAD DATA
    # ===============================
    data = get_notes(st.session_state.user["id"])

    # FILTER
    if st.session_state.view_mode == "pinned":
        data = [n for n in data if n["is_favorite"]]
    elif st.session_state.view_mode == "category":
        data = [n for n in data if n["category"] == st.session_state.filter_category]

    if st.session_state.search_query:
        q = st.session_state.search_query.lower()
        data = [
            n for n in data
            if q in n["title"].lower() or q in n["content"].lower()
        ]

    # ===============================
    # NOTES GRID (MASONRY)
    # ===============================
    st.markdown("<div class='masonry'>", unsafe_allow_html=True)

    for n in data:
        tc = get_text_color(n["color"])
        img_html = (
            f"<img class='note-img preview-img' src='data:image/png;base64,{n['image']}'>"
            if n["image"] else ""
        )

        st.markdown(
            f"""
            <div class="note-card {'pinned' if n['is_favorite'] else ''}"
                 style="background:{n['color']};color:{tc}">
                <div class="note-title">
                    {'⭐ ' if n['is_favorite'] else ''}{n['title']}
                </div>
                <div class="note-content">{n['content']}</div>
                {img_html}
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button(
            "⭐ Pin" if not n["is_favorite"] else "☆ Unpin",
            key=f"pin_{n['id']}"
        ):
            toggle_pin(n["id"], 0 if n["is_favorite"] else 1)
            st.rerun()

        if st.button("🗑️ Hapus", key=f"del_{n['id']}"):
            delete_note(n["id"])
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# FLOATING ACTION BUTTON (FAB)
# =====================================================
st.markdown("""
<style>
.fab {
    position: fixed;
    bottom: 70px;
    right: 20px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: #1a73e8;
    color: white;
    font-size: 32px;
    text-align: center;
    line-height: 56px;
    box-shadow: 0 4px 12px rgba(0,0,0,.3);
    z-index: 9999;
}
</style>
<div class="fab">+</div>
""", unsafe_allow_html=True)

# =====================================================
# BOTTOM NAV (MOBILE ONLY)
# =====================================================
st.markdown("""
<style>
.bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 56px;
    background: #ffffff;
    border-top: 1px solid #ddd;
    display: flex;
    justify-content: space-around;
    align-items: center;
    z-index: 9998;
}
.bottom-nav div {
    font-size: 14px;
}
@media (min-width: 769px) {
    .bottom-nav { display: none; }
}
</style>
<div class="bottom-nav">
  <div>🏠<br/>All</div>
  <div>⭐<br/>Pinned</div>
  <div>➕<br/>Add</div>
</div>
""", unsafe_allow_html=True)
