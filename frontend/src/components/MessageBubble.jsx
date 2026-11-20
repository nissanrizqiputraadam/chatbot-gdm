import { DropIcon } from "./Icons";

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
        {paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
    </div>
  );
}