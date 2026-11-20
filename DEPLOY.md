# Deploy chatbot GDM

Deploy backend dan frontend sebagai dua layanan publik. `localhost` hanya bisa
diakses dari perangkat yang menjalankannya.

## Backend di Render

1. Push proyek ini ke repository GitHub.
2. Di Render, pilih **New > Blueprint** dan hubungkan repository tersebut.
3. Render membaca `render.yaml`; lanjutkan pembuatan layanan `chatbot-gdm-api`.
4. Setelah deploy, buka alamat backend Render dan pastikan halaman `/` menampilkan
   `{"status":"ok"}`. Catat alamat itu, misalnya `https://chatbot-gdm-api.onrender.com`.

## Frontend di Vercel

1. Impor repository yang sama ke Vercel.
2. Atur **Root Directory** ke `frontend`.
3. Tambahkan environment variable `VITE_API_URL` dengan alamat backend Render,
   tanpa garis miring di akhir, misalnya `https://chatbot-gdm-api.onrender.com`.
4. Deploy dan catat domain frontend Vercel, misalnya `https://chatbot-gdm.vercel.app`.

## Hubungkan CORS

Di pengaturan layanan Render, isi `FRONTEND_ORIGINS` dengan domain frontend Vercel
yang sebenarnya, tanpa garis miring di akhir. Setelah itu, redeploy/restart backend.
Untuk domain frontend tambahan, pisahkan beberapa origin dengan koma.

Setiap perubahan `VITE_API_URL` di Vercel perlu diikuti redeploy frontend. Pengguna
kemudian membuka domain Vercel; mereka tidak perlu menjalankan server di perangkat
masing-masing.
