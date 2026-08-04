// Rendu markdown minimal pour les réponses du chatbot (titres, listes, gras).
// Volontairement sans dangerouslySetInnerHTML : on construit du JSX, pas du HTML brut.
function renderInline(text, keyPrefix) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? (
      <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>
    ) : (
      <span key={`${keyPrefix}-${i}`}>{part}</span>
    )
  );
}

export default function ChatMarkdown({ text }) {
  const lines = text.split('\n');
  const blocks = [];
  let listBuffer = [];

  const flushList = (key) => {
    if (listBuffer.length) {
      blocks.push(
        <ul key={`ul-${key}`}>
          {listBuffer.map((item, i) => (
            <li key={i}>{renderInline(item, `li-${key}-${i}`)}</li>
          ))}
        </ul>
      );
      listBuffer = [];
    }
  };

  lines.forEach((rawLine, idx) => {
    const line = rawLine.trim();

    if (!line) {
      flushList(idx);
      return;
    }

    const heading = line.match(/^(#{1,3})\s+(.*)/);
    if (heading) {
      flushList(idx);
      const Tag = `h${Math.min(heading[1].length + 3, 6)}`;
      blocks.push(<Tag key={idx}>{renderInline(heading[2], `h-${idx}`)}</Tag>);
      return;
    }

    const listItem = line.match(/^[-*]\s+(.*)/);
    if (listItem) {
      listBuffer.push(listItem[1]);
      return;
    }

    flushList(idx);
    blocks.push(<p key={idx}>{renderInline(line, `p-${idx}`)}</p>);
  });

  flushList('end');

  return <div className="chat-markdown">{blocks}</div>;
}
