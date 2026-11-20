import { useEffect, useRef, useState } from "react";
import MessageBubble from "./components/MessageBubble";
import { DropIcon, ArrowUpIcon } from "./components/Icons";
import { sendMessage } from "./api";
import "./App.css";

const TOPICS = [
  { q: "Apa itu diabetes gestasional?", hint: "Pengertian dan cara terjadinya" },
  { q: "Apa saja faktor risikonya?", hint: "Siapa yang lebih rentan" },
  { q: "Bagaimana cara diagnosisnya?", hint: "Tes gula darah selama hamil" },
  { q: "Berapa target gula darah ibu hamil?", hint: "Angka acuan yang umum dipakai" },
  { q: "Seberapa sering cek gula darah?", hint: "Cara memantau gula darah" },
];

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const started = messages.length > 0;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  async function handleSend(text) {
    const content = text.trim();
    if (!content || loading) return;

    setMessages((prev) => [
      ...prev,
      { id: Date.now(), role: "user", paragraphs: [content] },
    ]);
    setInput("");
    setLoading(true);

    try {
      const data = await sendMessage(content);
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, role: "bot", paragraphs: data.reply, kind: data.type },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "bot",
          paragraphs: ["Pesan belum terkirim karena server tidak merespons. Coba lagi beberapa saat lagi."],
          kind: "error",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e) {
    e.preventDefault();
    handleSend(input);
  }

  function resetChat() {
    setMessages([]);
    setInput("");
    inputRef.current?.focus();
  }

  return (
    <div className="page">
      <div className="sheet">
        <header className="top">
          <div className="brand">
            <span className="logo"><DropIcon size={20} /></span>
            <div>
              <h1>Asisten GDM</h1>
              <p>Diabetes pada kehamilan</p>
            </div>
          </div>
          {started && (
            <button className="ghost" onClick={resetChat} disabled={loading}>
              Percakapan baru
            </button>
          )}
        </header>

        <main className="log" role="log" aria-live="polite">
          {!started && (
            <section className="welcome">
              <h2>Halo, ada yang ingin Anda ketahui tentang diabetes gestasional?</h2>
              <p>Pilih satu topik di bawah ini, atau tulis pertanyaan Anda sendiri.</p>
              <ul className="topics">
                {TOPICS.map((t) => (
                  <li key={t.q}>
                    <button onClick={() => handleSend(t.q)} disabled={loading}>
                      <span className="t-title">{t.q}</span>
                      <span className="t-hint">{t.hint}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role} paragraphs={m.paragraphs} kind={m.kind} />
          ))}

          {loading && (
            <div className="msg bot">
              <span className="avatar"><DropIcon /></span>
              <div className="bubble bot typing" aria-label="Sedang mengetik">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </main>

        {started && (
          <div className="chips" aria-label="Topik cepat">
            {TOPICS.map((t) => (
              <button key={t.q} onClick={() => handleSend(t.q)} disabled={loading}>
                {t.q}
              </button>
            ))}
          </div>
        )}

        <form className="composer" onSubmit={onSubmit}>
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Tulis pertanyaan Anda"
            maxLength={500}
            aria-label="Pesan"
          />
          <button className="send" type="submit" disabled={loading || !input.trim()} aria-label="Kirim pesan">
            <ArrowUpIcon />
          </button>
        </form>

        <p className="note">
          Informasi ini bersifat edukatif, bukan diagnosis. Konsultasikan kondisi Anda
          dengan dokter atau tenaga kesehatan.
        </p>
      </div>
    </div>
  );
}