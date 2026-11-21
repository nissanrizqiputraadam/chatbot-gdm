import { DropIcon } from "./Icons";

function formatInline(text) {
  if (typeof text !== "string") return text;

  // Render teks di dalam **teks** menjadi <strong>teks</strong>
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function renderParagraph(p, index) {
  if (typeof p !== "string") return <p key={index}>{p}</p>;

  const trimmed = p.trim();

  // Jika paragraf adalah poin bullet (* atau -)
  if (trimmed.startsWith("* ") || trimmed.startsWith("- ")) {
    const content = trimmed.replace(/^[\*\-]\s+/, "");
    return (
      <p key={index} style={{ paddingLeft: "1.2em", textIndent: "-0.8em", margin: "0.3em 0" }}>
        <span>• </span>
        {formatInline(content)}
      </p>
    );
  }

  return <p key={index}>{formatInline(p)}</p>;
}

export default function MessageBubble({ role, paragraphs, kind }) {
  const isBot = role === "bot";
  return (
    <div className={`msg ${role}`}>
      {isBot && (
        <span className={`avatar ${kind === "emergency" ? "alert" : ""}`}>
          <DropIcon />
        </span>
      )}
      <div className={`bubble ${role} ${kind ?? ""}`}>
        {paragraphs.map((p, i) => renderParagraph(p, i))}
      </div>
    </div>
  );
}
