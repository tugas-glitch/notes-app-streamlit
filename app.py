import streamlit as st
import mysql.connector
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
    st.session_state.dark_mode = False   # DEFAULT = LIGHT
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "all"
if "filter_category" not in st.session_state:
    st.session_state.filter_category = "Semua"
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# =====================================================
# DATABASE
# =====================================================
def db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="notes_app",
        port=3306
    )

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
# NOTES (DB OPS)
# =====================================================
def get_notes(uid):
    con=db(); c=con.cursor(dictionary=True)
    c.execute(
        "SELECT * FROM notes WHERE user_id=%s ORDER BY is_favorite DESC, created_at DESC",
        (uid,)
    )
    data=c.fetchall(); con.close()
    return data

def add_note(uid,t,cg,col,ct,img):
    if not t or not ct:
        return
    con=db(); c=con.cursor()
    c.execute(
        "INSERT INTO notes(user_id,title,category,color,content,image) VALUES(%s,%s,%s,%s,%s,%s)",
        (uid,t,cg,col,ct,img)
    )
    con.commit(); con.close()

def delete_note(id):
    con=db(); c=con.cursor()
    c.execute("DELETE FROM notes WHERE id=%s",(id,))
    con.commit(); con.close()

def pin_note(id,v):
    con=db(); c=con.cursor()
    c.execute("UPDATE notes SET is_favorite=%s WHERE id=%s",(v,id))
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
            f"<b>{n['title']}</b><br/>Kategori: {n['category']}<br/><br/>{n['content']}",
            styles["Normal"]
        ))
        story.append(Spacer(1,10))
    doc.build(story)
    buf.seek(0)
    return buf
# =====================================================
# CSS (GOOGLE KEEP STYLE)
# =====================================================
st.markdown("""
<style>
.note-card {
    padding:16px;
    border-radius:18px;
    margin-bottom:16px;
    box-shadow:0 2px 6px rgba(0,0,0,0.15);
    transition:.2s;
}
.note-card:hover {
    box-shadow:0 6px 16px rgba(0,0,0,0.25);
    transform:translateY(-2px);
}
.note-title {
    font-size:16px;
    font-weight:600;
    margin-bottom:6px;
}
.note-content {
    font-size:14px;
    line-height:1.6;
    white-space:pre-wrap;
}
.note-img {
    margin-top:10px;
    border-radius:12px;
    max-width:100%;
}
.pinned {
    border:2px solid #f4c430;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# LIGHT / DARK MODE (STABLE)
# =====================================================
if st.session_state.dark_mode:
    st.markdown("""
    <style>
    .stApp { background:#202124; color:#e8eaed; }
    section.main h1,section.main h2,section.main h3,
    section.main p,section.main label,section.main span {
        color:#e8eaed !important;
    }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    .stApp { background:#ffffff; color:#202124; }
    section.main h1,section.main h2,section.main h3,
    section.main p,section.main label,section.main span {
        color:#202124 !important;
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
        value=st.session_state.search_query
    )

    if st.button("📝 Semua Catatan", use_container_width=True):
        st.session_state.view_mode="all"
    if st.button("⭐ Pinned", use_container_width=True):
        st.session_state.view_mode="pinned"

    st.markdown("---")
    cat = st.selectbox(
        "📂 Kategori",
        ["Semua","Pribadi","Kerja","Kuliah","Ide","Lainnya"],
        index=["Semua","Pribadi","Kerja","Kuliah","Ide","Lainnya"]
        .index(st.session_state.filter_category)
    )
    st.session_state.filter_category=cat
    if cat!="Semua":
        st.session_state.view_mode="category"

    st.markdown("---")
    st.markdown("### 📄 Export PDF")
    pdf_cat = st.selectbox(
        "Kategori PDF",
        ["Semua","Pribadi","Kerja","Kuliah","Ide","Lainnya"],
        key="pdf_sidebar"
    )
    st.download_button(
        "⬇️ Download PDF",
        export_pdf(
            get_notes(st.session_state.user["id"]) if st.session_state.user else [],
            pdf_cat
        ),
        "notes.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    st.markdown("---")
    st.toggle("🌙 Dark Mode", key="dark_mode")

    if st.session_state.user:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user=None
            st.experimental_rerun()

# =====================================================
# AUTH
# =====================================================
def login(u,p):
    con=db(); c=con.cursor(dictionary=True)
    c.execute("SELECT * FROM users WHERE username=%s",(u,))
    user=c.fetchone(); con.close()
    if user and bcrypt.checkpw(p.encode(), user["password"].encode()):
        return user

def register(u,p):
    con=db(); c=con.cursor()
    c.execute("SELECT id FROM users WHERE username=%s",(u,))
    if c.fetchone():
        con.close()
        return False,"Username sudah ada"
    h=bcrypt.hashpw(p.encode(),bcrypt.gensalt()).decode()
    c.execute("INSERT INTO users(username,password) VALUES(%s,%s)",(u,h))
    con.commit(); con.close()
    return True,"Registrasi berhasil"

def reset_pw(u,p):
    con=db(); c=con.cursor()
    h=bcrypt.hashpw(p.encode(),bcrypt.gensalt()).decode()
    c.execute("UPDATE users SET password=%s WHERE username=%s",(h,u))
    con.commit(); con.close()
    return True
# =====================================================
# AUTH PAGE
# =====================================================
if not st.session_state.user:
    st.title("📝 Notes App")

    c1,c2,c3=st.columns(3)
    if c1.button("Login"): st.session_state.auth_mode="login"
    if c2.button("Register"): st.session_state.auth_mode="register"
    if c3.button("Reset"): st.session_state.auth_mode="reset"

    if st.session_state.auth_mode=="login":
        u=st.text_input("Username")
        p=st.text_input("Password",type="password")
        if st.button("Masuk"):
            user=login(u,p)
            if user:
                st.session_state.user=user
                st.experimental_rerun()
            else:
                st.error("Login gagal")

    elif st.session_state.auth_mode=="register":
        u=st.text_input("Username")
        p=st.text_input("Password",type="password")
        if st.button("Daftar"):
            ok,msg=register(u,p)
            st.success(msg) if ok else st.error(msg)

    else:
        u=st.text_input("Username")
        p=st.text_input("Password Baru",type="password")
        if st.button("Reset Password"):
            reset_pw(u,p)
            st.success("Password direset")

# =====================================================
# MAIN APP
# =====================================================
else:
    user=st.session_state.user
    st.title("📒 Catatan Saya")

    with st.expander("➕ Tambah Catatan"):
        t=st.text_input("Judul")
        cg=st.selectbox("Kategori",["Pribadi","Kerja","Kuliah","Ide","Lainnya"])
        col=st.color_picker("Warna","#FFF9C4")
        ct=st.text_area("Isi Catatan")
        img=st.file_uploader("Gambar (opsional)",["png","jpg","jpeg"])
        if st.button("Simpan Catatan"):
            add_note(user["id"],t,cg,col,ct,img_to_b64(img))
            st.experimental_rerun()

    data=get_notes(user["id"])

    if st.session_state.view_mode=="pinned":
        data=[n for n in data if n["is_favorite"]]
    elif st.session_state.view_mode=="category" and st.session_state.filter_category!="Semua":
        data=[n for n in data if n["category"]==st.session_state.filter_category]

    if st.session_state.search_query:
        q=st.session_state.search_query.lower()
        data=[n for n in data if q in n["title"].lower() or q in n["content"].lower()]

    cols=st.columns(3)
    for i,n in enumerate(data):
        with cols[i%3]:
            tc=get_text_color(n["color"])
            img_html = f"<img class='note-img' src='data:image/png;base64,{n['image']}'>" if n.get("image") else ""
            st.markdown(
                f"<div class='note-card {'pinned' if n['is_favorite'] else ''}' "
                f"style='background:{n['color']};color:{tc}'>"
                f"<div class='note-title'>{'⭐ ' if n['is_favorite'] else ''}{n['title']}</div>"
                f"<div class='note-content'>{n['content']}</div>{img_html}</div>",
                unsafe_allow_html=True
            )
            if st.button("⭐ Pin" if not n["is_favorite"] else "☆ Unpin", key=f"pin{n['id']}"):
                pin_note(n["id"],0 if n["is_favorite"] else 1)
                st.experimental_rerun()
            if st.button("🗑️ Hapus", key=f"del{n['id']}"):
                delete_note(n["id"])
                st.experimental_rerun()
