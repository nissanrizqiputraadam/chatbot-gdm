export default function SummaryCard({ data, onRestart }) {
  const badgeLabel =
    data.sumber === "gemini"
      ? "Diringkas oleh AI"
      : data.sumber === "extractive"
      ? "Ringkasan otomatis"
      : null;

  return (
    <section className="summary" aria-label="Ringkasan percakapan">
      {/* Header */}
      <div className="summary-header">
        <h2>Ringkasan percakapan</h2>
        {badgeLabel && <span className="summary-badge">{badgeLabel}</span>}
      </div>

      {data.ringkasan && <p className="summary-meta">{data.ringkasan}</p>}

      {/* Kesimpulan utama – hasil text summarization */}
      {data.kesimpulan && (
        <div className="summary-conclusion">
          <h3>Kesimpulan</h3>
          <p>{data.kesimpulan}</p>
        </div>
      )}

      {/* Saran */}
      {data.saran?.length > 0 && (
        <>
          <h3>Saran</h3>
          <ul>
            {data.saran.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </>
      )}

      {/* Catatan khusus (darurat / angka pribadi / di luar topik) */}
      {data.catatan?.length > 0 && (
        <div className="summary-note">
          {data.catatan.map((c) => (
            <p key={c}>{c}</p>
          ))}
        </div>
      )}

      <div className="summary-actions">
        <button className="btn primary" onClick={onRestart}>
          Mulai percakapan baru
        </button>
      </div>
    </section>
  );
}
