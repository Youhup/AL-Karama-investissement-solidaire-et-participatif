import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { sendChatMessage, startConversation } from '../api/chat';
import ChatMarkdown from './ChatMarkdown';

const INTRO_MESSAGE = {
  sender: 'assistant',
  content: "Bonjour 👋 Je peux vous parler de la plateforme, de l'économie sociale et solidaire, ou vous aider à préparer un dossier. Que souhaitez-vous savoir ? 😊",
};

// ChatWidget est monté une seule fois au niveau de <App> (en dehors de
// <Routes>) pour rester visible sur toutes les pages : useParams() n'y
// fonctionne donc pas (il faut être sous un <Route> pour ça). On retrouve
// l'id du projet consulté en analysant l'URL courante à la place.
const PROJECT_ID_ROUTES = [/^\/projets\/([^/]+)/, /^\/mes-projets\/([^/]+)/, /^\/admin\/projects\/([^/]+)/];

function currentProjectIdFromPath(pathname) {
  for (const pattern of PROJECT_ID_ROUTES) {
    const match = pathname.match(pattern);
    if (match) return match[1];
  }
  return null;
}

export default function ChatWidget() {
  const { user } = useAuth();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([INTRO_MESSAGE]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const conversationIdRef = useRef(null);
  const scrollRef = useRef(null);

  const contextRole = user ? user.role : 'visiteur';
  const projectId = currentProjectIdFromPath(location.pathname);

  // Le même <ChatWidget> reste monté sur toute la session (changement de
  // compte, navigation entre projets) : sans ça, l'historique d'un ancien
  // compte reste affiché, et la conversation garde le project_id de la
  // première page visitée même si on change de projet.
  const resetKey = `${user ? user.id : 'anonyme'}:${projectId ?? ''}`;
  const previousResetKeyRef = useRef(resetKey);

  useEffect(() => {
    if (previousResetKeyRef.current !== resetKey) {
      previousResetKeyRef.current = resetKey;
      conversationIdRef.current = null;
      setMessages([INTRO_MESSAGE]);
      setError('');
    }
  }, [resetKey]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, open]);

  async function handleSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    setError('');
    setMessages((m) => [...m, { sender: 'user', content: text }]);
    setInput('');
    setSending(true);

    try {
      if (!conversationIdRef.current) {
        const { conversation_id } = await startConversation(contextRole, projectId);
        conversationIdRef.current = conversation_id;
      }
      // Le 1er fragment reçu crée le message assistant, les suivants
      // remplacent juste son contenu — effet "machine à écrire" progressif.
      // NB : on détermine "premier fragment ?" à partir de `m` (le dernier
      // message est alors forcément celui de l'utilisateur qu'on vient
      // d'ajouter) plutôt que via une variable externe mutée dans l'updater
      // — StrictMode appelle deux fois les updaters de setState en dev, et
      // une variable externe mutée y survit entre les deux appels, ce qui
      // écrasait le message utilisateur au lieu d'ajouter celui de l'assistant.
      await sendChatMessage(conversationIdRef.current, text, (full) => {
        setMessages((m) => {
          const last = m[m.length - 1];
          if (last?.sender !== 'assistant') {
            return [...m, { sender: 'assistant', content: full }];
          }
          const copy = [...m];
          copy[copy.length - 1] = { sender: 'assistant', content: full };
          return copy;
        });
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="chat-widget">
      {open && (
        <div className="chat-panel">
          <div className="chat-panel-header">
            <span>Assistant Al Karama</span>
            <button className="chat-close" onClick={() => setOpen(false)} aria-label="Fermer">×</button>
          </div>

          <div className="chat-panel-messages" ref={scrollRef}>
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.sender === 'user' ? 'user' : 'bot'}`}>
                {m.sender === 'user' ? m.content : <ChatMarkdown text={m.content} />}
              </div>
            ))}
            {sending && messages[messages.length - 1]?.sender !== 'assistant' && (
              <div className="msg bot chat-typing">...</div>
            )}
          </div>

          {error && <div className="chat-error">{error}</div>}

          <form className="chat-input-row" onSubmit={handleSend}>
            <input
              type="text" value={input} onChange={(e) => setInput(e.target.value)}
              placeholder="Écrivez votre message..." disabled={sending}
            />
            <button type="submit" disabled={sending || !input.trim()}>Envoyer</button>
          </form>
        </div>
      )}

      <button className="chat-fab" onClick={() => setOpen((o) => !o)} aria-label="Ouvrir l'assistant">
        {open ? '×' : '💬'}
      </button>
    </div>
  );
}
