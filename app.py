import streamlit as st
import sqlite3
import bcrypt
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import base64

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Notes App", layout="wide")

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

# =====================================================
# DATABASE (SQLITE)
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
# NOTES
# =====================================================
def get_notes(uid):
    con=db(); c=con.cursor()
    c.execute("""
        SELECT * FROM notes
        WHERE user_id=?
        ORDER BY is_favorite DESC, created_at DESC
    """,(uid,))
    rows=c.fetchall(); con.close()

    keys=["id","user_id","title","category","color","content","image","is_favorite","created_at"]
    return [dict(zip(keys,r)) for r in rows]

def add_note(uid,t,cg,col,ct,img):
    if not t or not ct: return
    con=db(); c=con.cursor()
    c.execute("""
        INSERT INTO notes(user_id,title,category,color,content,image)
        VALUES(?,?,?,?,?,?)
    """,(uid,t,cg,col,ct,img))
    con.commit(); con.close()

def delete_note(id):
    con=db(); c=con.cursor()
    c.execute("DELETE FROM notes WHERE id=?",(id,))
    con.commit(); con.close()

def pin_note(id,v):
    con=db(); c=con.cursor()
    c.execute("UPDATE notes SET is_favorite=? WHERE id=?",(v,id))
    con.commit(); con.close()

# =====================================================
# PDF
# =====================================================
def export_pdf(data,cat):
    if cat!="Semua":
        data=[n for n in data if n["category"]==cat]
    buf=BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4)
    styles=getSampleStyleSheet()
    story=[Paragraph(f"<b>NOTES - {cat}</b>",styles["Title"]),Spacer(1,12)]
    for n in data:
        story.append(Paragraph(
            f"<b>{n['title']}</b><br/>{n['content']}",
            styles["Normal"]
        ))
        story.append(Spacer(1,10))
    doc.build(story)
    buf.seek(0)
    return buf

# =====================================================
# CSS + THEME
# =====================================================
st.markdown("""
<style>
.note-card{
 padding:16px;border-radius:18px;margin-bottom:16px;
 box-shadow:0 2px 6px rgba(0,0,0,.15);transition:.2s}
.note-card:hover{box-shadow:0 6px 16px rgba(0,0,0,.25)}
.note-title{font-size:16px;font-weight:600;margin-bottom:6px}
.note-content{font-size:14px;white-space:pre-wrap}
.note-img{margin-top:10px;border-radius:12px;max-width:100%}
.pinned{border:2px solid #f4c430}
</style>
""", unsafe_allow_html=True)

if st.session_state.dark_mode:
    st.markdown("<style>.stApp{background:#202124;color:#e8eaed}</style>",unsafe_allow_html=True)
else:
    st.markdown("<style>.stApp{background:#ffffff;color:#202124}</style>",unsafe_allow_html=True)

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.markdown("## 🗂️ Notes")
    st.session_state.search_query = st.text_input("🔍 Cari")

    if st.button("📝 Semua"): st.session_state.view_mode="all"
    if st.button("⭐ Pinned"): st.session_state.view_mode="pinned"

    cat = st.selectbox(
        "📂 Kategori",
        ["Semua","Pribadi","Kerja","Kuliah","Ide","Lainnya"]
    )
    st.session_state.filter_category=cat
    if cat!="Semua": st.session_state.view_mode="category"

    st.markdown("### 📄 Export PDF")
    pdf_cat = st.selectbox("Kategori PDF",["Semua","Pribadi","Kerja","Kuliah","Ide","Lainnya"])
    st.download_button(
        "⬇️ Download",
        export_pdf(get_notes(st.session_state.user["id"]) if st.session_state.user else [], pdf_cat),
        "notes.pdf",
        mime="application/pdf"
    )

    st.toggle("🌙 Dark Mode", key="dark_mode")
# =====================================================
# AUTH
# =====================================================
def login(u,p):
    con=db(); c=con.cursor()
    c.execute("SELECT * FROM users WHERE username=?",(u,))
    r=c.fetchone(); con.close()
    if r and bcrypt.checkpw(p.encode(), r[2].encode()):
        return {"id":r[0],"username":r[1]}

def register(u,p):
    con=db(); c=con.cursor()
    try:
        h=bcrypt.hashpw(p.encode(),bcrypt.gensalt()).decode()
        c.execute("INSERT INTO users(username,password) VALUES(?,?)",(u,h))
        con.commit()
        return True
    except:
        return False
    finally:
        con.close()

# =====================================================
# AUTH PAGE
# =====================================================
if not st.session_state.user:
    st.title("📝 Notes App")

    if st.session_state.auth_mode=="login":
        u=st.text_input("Username")
        p=st.text_input("Password",type="password")
        if st.button("Login"):
            user=login(u,p)
            if user:
                st.session_state.user=user
                st.experimental_rerun()
            else:
                st.error("Login gagal")

    if st.button("Register"):
        st.session_state.auth_mode="register"

    if st.session_state.auth_mode=="register":
        u=st.text_input("Username")
        p=st.text_input("Password",type="password")
        if st.button("Daftar"):
            if register(u,p):
                st.success("Registrasi berhasil")
                st.session_state.auth_mode="login"
            else:
                st.error("Username sudah ada")

# =====================================================
# MAIN APP
# =====================================================
else:
    st.title("📒 Catatan Saya")

    with st.expander("➕ Tambah Catatan"):
        t=st.text_input("Judul")
        cg=st.selectbox("Kategori",["Pribadi","Kerja","Kuliah","Ide","Lainnya"])
        col=st.color_picker("Warna","#FFF9C4")
        ct=st.text_area("Isi")
        img=st.file_uploader("Gambar",["png","jpg","jpeg"])
        if st.button("Simpan"):
            add_note(st.session_state.user["id"],t,cg,col,ct,img_to_b64(img))
            st.experimental_rerun()

    data=get_notes(st.session_state.user["id"])

    if st.session_state.view_mode=="pinned":
        data=[n for n in data if n["is_favorite"]]
    elif st.session_state.view_mode=="category":
        data=[n for n in data if n["category"]==st.session_state.filter_category]

    if st.session_state.search_query:
        q=st.session_state.search_query.lower()
        data=[n for n in data if q in n["title"].lower() or q in n["content"].lower()]

    cols=st.columns(3)
    for i,n in enumerate(data):
        with cols[i%3]:
            tc=get_text_color(n["color"])
            img_html=f"<img class='note-img' src='data:image/png;base64,{n['image']}'>" if n["image"] else ""
            st.markdown(
                f"<div class='note-card {'pinned' if n['is_favorite'] else ''}' style='background:{n['color']};color:{tc}'>"
                f"<div class='note-title'>{'⭐ ' if n['is_favorite'] else ''}{n['title']}</div>"
                f"<div class='note-content'>{n['content']}</div>{img_html}</div>",
                unsafe_allow_html=True
            )
            if st.button("⭐ Pin" if not n["is_favorite"] else "☆ Unpin", key=f"p{n['id']}"):
                pin_note(n["id"],0 if n["is_favorite"] else 1)
                st.experimental_rerun()
            if st.button("🗑️ Hapus", key=f"d{n['id']}"):
                delete_note(n["id"])
                st.experimental_rerun()
