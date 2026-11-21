# Panduan Menjalankan Chatbot GDM + RAG (Untuk Tim)

Panduan ini ditujukan agar seluruh anggota tim dapat menjalankan project ini dengan mudah menggunakan satu perintah: `npm run dev:all`.

---

## 1. Prasyarat Sistem

Pastikan di laptop masing-masing sudah terpasang:
- **Python** (versi 3.10 atau lebih baru)
- **Node.js** (versi 18 atau lebih baru) & **npm**
- *(Opsional)* **Ollama** jika ingin menjalankan model AI secara offline lokal

Cek di terminal masing-masing:
```powershell
python --version
node --version
npm --version
```

---

## 2. Persiapan Awal (Hanya dilakukan sekali)

### Langkah A: Buat File `.env` di Backend
Karena file `.env` berisi kunci rahasia dan tidak di-commit ke Git, buat file baru bernama `.env` di dalam folder `backend/`:

Salin isi dari `backend/.env.example` atau isi langsung seperti ini di `backend/.env`:
```env
GEMINI_API_KEY=masukkan_api_key_gemini_anda_di_sini
OLLAMA_URL=http://localhost:11434/api/chat
OLLAMA_MODEL=qwen2.5:1.5b
LLM_PROVIDER=auto
```

### Langkah B: Install Dependensi Backend (Python)
Buka terminal di root project (`chatbot-gdm`):
```powershell
python -m pip install -r backend/requirements.txt
```

### Langkah C: Install Dependensi Frontend (Node.js)
Masuk ke folder `frontend` dan install paket:
```powershell
cd frontend
npm install
cd ..
```

---

## 3. Menjalankan Project (`npm run dev:all`)

Cukup jalankan satu perintah berikut dari **folder utama (`chatbot-gdm`)**:

```powershell
npm run dev:all
```
*(Catatan untuk pengguna Windows PowerShell: jika muncul pesan error permission script `npm.ps1`, gunakan `npm.cmd run dev:all`)*

Perintah ini akan secara otomatis:
1. Mendeteksi versi Python di laptop Anda (`py`, `python`, atau `python3`).
2. Menjalankan **Backend FastAPI (Uvicorn)** di port `8000`.
3. Menjalankan **Frontend Vite (React)** di port `5173`.

---

## 4. Akses Aplikasi

Buka browser dan kunjungi:
- **Chatbot Web:** [http://localhost:5173](http://localhost:5173)
- **Status Backend:** [http://localhost:8000/](http://localhost:8000/) *(menampilkan `{"status":"ok", "rag_loaded":true}`)*

---

## 5. Menghentikan Project

Tekan **`Ctrl + C`** di terminal yang sedang menjalankan project. Backend dan Frontend akan otomatis dimatikan secara bersamaan.

---

## 6. Pertanyaan Umum & Troubleshooting

### Q: Muncul pesan `npm.ps1 cannot be loaded because running scripts is disabled`
Gunakan `npm.cmd`:
```powershell
npm.cmd run dev:all
```

### Q: Muncul `Tidak dapat menghubungi backend` di browser
Pastikan terminal `npm run dev:all` tidak error saat start backend. Pastikan juga semua package di `backend/requirements.txt` sudah ter-install dengan benar.

### Q: Ingin mode 100% offline tanpa internet
1. Pastikan aplikasi **Ollama** aktif di komputer dengan model `qwen2.5:1.5b`.
2. Buka `backend/.env`, ubah:
   ```env
   LLM_PROVIDER=ollama
   ```
