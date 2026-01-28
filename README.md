<img width="1366" height="641" alt="Screenshot 2026-01-28 060754" src="https://github.com/user-attachments/assets/271ff86f-0ba0-4ddc-be87-281d488b9348" />


# 📝 Notes App – Streamlit

Aplikasi **catatan (Notes App)** berbasis **Streamlit** dengan tampilan modern ala **Google Keep**.  
Mendukung autentikasi user, kategori, pinned notes, upload gambar, export PDF, serta mode light/dark.

Aplikasi ini dibuat untuk **tugas, demo, dan portfolio**, serta **siap dideploy ke Streamlit Cloud**.

---

## 🚀 Fitur Utama

- 🔐 **Authentication**
  
  - Login
  
  - Register
  
  - Session management

- 🗒️ **Manajemen Catatan**

  - Tambah / hapus catatan

  - Kategori (Pribadi, Kerja, Kuliah, Ide, dll)

  - Warna catatan

  - Upload gambar (opsional)

  - Pin / unpin catatan

- 🔍 **Pencarian & Filter**

  - Search catatan (judul & isi)

  - Filter kategori

  - Tampilan pinned terpisah

- 📄 **Export PDF**

  - Export semua catatan

  - Export berdasarkan kategori

  - Download langsung dari sidebar

- 🌙 **Light / Dark Mode**

  - Default: Light Mode

  - Toggle Dark Mode manual

  - UI stabil & nyaman dibaca

- 🎨 **UI Modern**

  - Card style ala Google Keep

  - Sidebar navigasi

  - Responsive layout (desktop friendly)

---

## 🛠️ Teknologi yang Digunakan

- **Python 3**

- **Streamlit**

- **SQLite** (database lokal, auto-create)

- **bcrypt** (password hashing)

- **ReportLab** (PDF export)

---

## 📂 Struktur Project

notes-app-streamlit/

│

├── app.py

├── requirements.txt

├── README.md

└── .gitignore


---

## ▶️ Cara Menjalankan Secara Lokal

1. Clone repository:

   ```bash

   git clone https://github.com/USERNAME/notes-app-streamlit.git

   cd notes-app-streamlit

2. Install dependencies:

    ```bash

    pip install -r requirements.txt

3. Jalankan aplikasi:

  ```bash

  streamlit run app.py


4. Buka browser:

  http://localhost:8501
