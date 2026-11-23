import { useEffect, useRef, useState } from "react";
import MessageBubble from "./components/MessageBubble";
import SummaryCard from "./components/SummaryCard";
import Landing from "./components/Landing";
import { DropIcon, ArrowUpIcon } from "./components/Icons";
import { sendMessage, getSummary } from "./api";
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
  // Selalu mulai dari Landing; hash #chatbot hanya dipakai untuk navigasi maju/mundur
  const [showChat, setShowChat] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Ringkasan sesi
  const [summary, setSummary] = useState(null);
  const [summarizing, setSummarizing] = useState(false);
  const [summaryError, setSummaryError] = useState(false);

  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const started = messages.length > 0;
  const busy = loading || summarizing;
  const ended = summary !== null;
  const canSummarize = messages.some((m) => m.role === "bot" && m.question);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading, summarizing, summary, summaryError]);

  useEffect(() => {
    const chatHash = "#chatbot";
    const baseUrl = `${window.location.pathname}${window.location.search}`;

    // Jika URL dibuka langsung dengan #chatbot, bersihkan hash dan mulai dari landing
    if (window.location.hash === chatHash) {
      window.history.replaceState({ screen: "landing" }, "", baseUrl);
      setShowChat(false);
    }

    const syncScreenWithHistory = () => {
      setShowChat(window.location.hash === chatHash);
    };
    window.addEventListener("popstate", syncScreenWithHistory);
    return () => window.removeEventListener("popstate", syncScreenWithHistory);
  }, []);

  async function handleSend(text) {
    const content = text.trim();
    if (!content || busy || ended) return;

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
        {
          id: Date.now() + 1,
          role: "bot",
          paragraphs: data.reply,
          kind: data.type,
          intent: data.intent ?? null, // dipakai untuk ringkasan
          question: content,           // dipakai untuk ringkasan
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "bot",
          paragraphs: [error.message || "Pesan gagal dikirim. Periksa apakah backend berjalan."],
          kind: "error",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function endChat() {
    if (busy || ended) return;

    const items = messages
      .filter((m) => m.role === "bot" && m.question)
      .map((m) => ({
        question: m.question,
        intent: m.intent ?? null,
        type: m.kind ?? "answer",
        answer: m.paragraphs ?? [],   // kirim paragraf jawaban bot untuk dirangkum
      }));
    if (items.length === 0) return;

    setSummarizing(true);
    setSummaryError(false);
    try {
      setSummary(await getSummary(items));
    } catch {
      setSummaryError(true);
    } finally {
      setSummarizing(false);
    }
  }

  function onSubmit(e) {
    e.preventDefault();
    handleSend(input);
  }

  function resetChat() {
    setMessages([]);
    setInput("");
    setSummary(null);
    setSummaryError(false);
    requestAnimationFrame(() => inputRef.current?.focus());
  }

  function openChat() {
    const url = `${window.location.pathname}${window.location.search}#chatbot`;
    window.history.pushState({ screen: "chat" }, "", url);
    setShowChat(true);
  }

  function returnToLanding() {
    if (window.location.hash === "#chatbot") {
      window.history.back();
    } else {
      setShowChat(false);
    }
  }

  if (!showChat) {
    return <Landing onAsk={openChat} />;
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
          <div className="top-actions">
            <button className="ghost" onClick={returnToLanding} disabled={busy}>
              Beranda
            </button>
            {canSummarize && !ended && (
              <button className="ghost" onClick={endChat} disabled={busy}>
                {summarizing ? "Menyusun…" : "Akhiri & ringkas"}
              </button>
            )}
            {started && (
              <button className="ghost" onClick={resetChat} disabled={busy}>
                Percakapan baru
              </button>
            )}
          </div>
        </header>

        <main className="log" role="log" aria-live="polite">
          {!started && (
            <section className="welcome">
              <h2>Halo, ada yang ingin Anda ketahui tentang diabetes gestasional?</h2>
              <p>Pilih satu topik di bawah ini, atau tulis pertanyaan Anda sendiri.</p>
              <ul className="topics">
                {TOPICS.map((t) => (
                  <li key={t.q}>
                    <button onClick={() => handleSend(t.q)} disabled={busy}>
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

          {busy && (
            <div className="msg bot">
              <span className="avatar"><DropIcon /></span>
              <div
                className="bubble bot typing"
                aria-label={summarizing ? "Menyusun ringkasan" : "Sedang mengetik"}
              >
                <span></span><span></span><span></span>
              </div>
            </div>
          )}

          {summaryError && (
            <p className="summary-error">
              Ringkasan belum dapat dibuat. Coba lagi beberapa saat lagi.
            </p>
          )}

          {summary && <SummaryCard data={summary} onRestart={resetChat} />}

          <div ref={bottomRef} />
        </main>

        {started && !ended && (
          <div className="chips" aria-label="Topik cepat">
            {TOPICS.map((t) => (
              <button key={t.q} onClick={() => handleSend(t.q)} disabled={busy}>
                {t.q}
              </button>
            ))}
          </div>
        )}

        {!ended && (
          <form className="composer" onSubmit={onSubmit}>
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Tulis pertanyaan Anda"
              maxLength={500}
              aria-label="Pesan"
            />
            <button
              className="send"
              type="submit"
              disabled={busy || !input.trim()}
              aria-label="Kirim pesan"
            >
              <ArrowUpIcon />
            </button>
          </form>
        )}

        <p className="note">
          Informasi ini bersifat edukatif, bukan diagnosis. Konsultasikan kondisi Anda
          dengan dokter atau tenaga kesehatan.
        </p>
      </div>
    </div>
  );
}