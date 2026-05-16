/**
 * ChatPanel — fixed bottom chat panel for InvestIQ.
 *
 * UI-SPEC: collapsed 44px bar at page bottom; click expands to 300px panel
 * with scrollable message history, animated loading dots, and keyboard submit.
 *
 * Props:
 *   briefing {object|null} - Full briefing from GET /api/briefing (passed to sendChat)
 */
import React, { useState, useRef, useEffect } from 'react';
import { sendChat } from '../api.js';

export default function ChatPanel({ briefing }) {
  const [expanded, setExpanded] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Ask me anything about today's briefing." }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll to the latest message when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMessage = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);
    try {
      const response = await sendChat(userMessage, briefing);
      setMessages(prev => [...prev, { role: 'assistant', content: response }]);
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: "Something went wrong — try again." }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        height: expanded ? '300px' : '44px',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Toggle bar — always rendered */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          height: '44px',
          background: '#1A1A2E',
          flexShrink: 0,
          borderTop: '1px solid rgba(255,255,255,0.1)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
          cursor: 'pointer',
          justifyContent: 'space-between',
        }}
      >
        <span style={{ fontSize: 14, color: 'rgba(255,255,255,0.8)' }}>
          Ask me anything about today's briefing.
        </span>
        <span style={{ color: 'white', fontSize: 16 }}>
          {expanded ? '˅' : '˄'}
        </span>
      </div>

      {/* Expanded body */}
      {expanded && (
        <div
          style={{
            flex: 1,
            background: '#1A1A2E',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Message list */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '12px 24px',
            }}
          >
            {messages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  marginBottom: 8,
                }}
              >
                <div
                  style={{
                    background:
                      msg.role === 'user' ? '#0066CC' : 'rgba(255,255,255,0.08)',
                    color:
                      msg.role === 'user' ? '#fff' : 'rgba(255,255,255,0.9)',
                    borderRadius:
                      msg.role === 'user'
                        ? '12px 12px 2px 12px'
                        : '12px 12px 12px 2px',
                    padding: '8px 12px',
                    maxWidth: '70%',
                    fontSize: 14,
                  }}
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {/* Loading dots */}
            {loading && (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  marginBottom: 8,
                }}
              >
                <div
                  style={{
                    background: 'rgba(255,255,255,0.08)',
                    color: 'rgba(255,255,255,0.9)',
                    borderRadius: '12px 12px 12px 2px',
                    padding: '8px 12px',
                  }}
                >
                  <div className="typing-dots">
                    <span>•</span>
                    <span>•</span>
                    <span>•</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input row */}
          <div
            style={{
              height: '52px',
              padding: '8px 24px',
              borderTop: '1px solid rgba(255,255,255,0.1)',
              display: 'flex',
              gap: 8,
              background: '#1A1A2E',
            }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              disabled={loading}
              placeholder="Ask about a holding, signal, or recommendation…"
              style={{
                flex: 1,
                background: 'rgba(255,255,255,0.1)',
                border: '1px solid rgba(255,255,255,0.2)',
                borderRadius: 4,
                color: 'white',
                fontSize: 14,
                padding: '8px 12px',
              }}
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              style={{
                padding: '8px 16px',
                background: '#0066CC',
                color: '#fff',
                border: 'none',
                borderRadius: 4,
                fontSize: 14,
                fontWeight: 600,
                cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                opacity: loading || !input.trim() ? 0.6 : 1,
              }}
            >
              Send Message
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
