import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, BookOpen, Clock, AlertTriangle, Sparkles, Sprout } from 'lucide-react';
import { sendQuery, streamQuery } from '../api/client';

const SUGGESTED_QUERIES = [
  "What is the dose of sulfosulfuron for wheat?",
  "How do I control whitefly in cotton?",
  "When should I sow wheat in Punjab?",
  "Phalaris minor control in wheat"
];

// Simple helper to format text formatting (bolding, lists, linebreaks, table-stripping safety net)
const FormattedText = ({ text, isStreaming }) => {
  if (!text && !isStreaming) return null;

  // Split by line breaks
  const lines = (text || '').split('\n');

  return (
    <div className="space-y-2 text-sm md:text-base leading-relaxed text-emerald-50">
      {lines.map((line, idx) => {
        const isLastLine = idx === lines.length - 1;
        let trimmed = line.trim();
        if (!trimmed && !isLastLine) return <div key={idx} className="h-1" />;

        // Safety Net: Skip table header separator lines like |---|---|
        if (/^\|?\s*[-:]+(\s*\|\s*[-:]+)+\s*\|?$/.test(trimmed)) {
          return null;
        }

        // Safety Net: If line starts and ends with | (table row), clean pipes into natural text
        if (trimmed.includes('|')) {
          trimmed = trimmed
            .split('|')
            .map(cell => cell.trim())
            .filter(Boolean)
            .join(' — ');
        }

        // Header / bold section titles
        if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
          return (
            <h4 key={idx} className="font-semibold text-emerald-300 text-base md:text-lg mt-3 mb-1">
              {trimmed.replace(/\*\*/g, '')}
              {isLastLine && isStreaming && (
                <span className="inline-block w-2 h-4 ml-1 bg-emerald-400 animate-pulse rounded-sm align-middle" />
              )}
            </h4>
          );
        }

        // Bullet points
        if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
          const content = trimmed.substring(2);
          return (
            <div key={idx} className="flex items-start gap-2.5 ml-2 my-1">
              <span className="text-emerald-400 mt-1.5 text-xs">•</span>
              <div>
                <span dangerouslySetInnerHTML={{ __html: formatInline(content) }} />
                {isLastLine && isStreaming && (
                  <span className="inline-block w-2 h-4 ml-1 bg-emerald-400 animate-pulse rounded-sm align-middle" />
                )}
              </div>
            </div>
          );
        }

        // Numbered items
        if (/^\d+\.\s/.test(trimmed)) {
          const match = trimmed.match(/^(\d+\.)\s+(.*)/);
          return (
            <div key={idx} className="flex items-start gap-2 ml-2 my-1">
              <span className="font-semibold text-emerald-400 text-sm min-w-[20px]">{match[1]}</span>
              <div>
                <span dangerouslySetInnerHTML={{ __html: formatInline(match[2]) }} />
                {isLastLine && isStreaming && (
                  <span className="inline-block w-2 h-4 ml-1 bg-emerald-400 animate-pulse rounded-sm align-middle" />
                )}
              </div>
            </div>
          );
        }

        return (
          <p key={idx}>
            <span dangerouslySetInnerHTML={{ __html: formatInline(trimmed) }} />
            {isLastLine && isStreaming && (
              <span className="inline-block w-2 h-4 ml-1 bg-emerald-400 animate-pulse rounded-sm align-middle" />
            )}
          </p>
        );
      })}
    </div>
  );
};

function formatInline(str) {
  if (!str) return '';
  return str
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-emerald-200">$1</strong>')
    .replace(/`(.*?)`/g, '<code class="bg-emerald-900/60 px-1.5 py-0.5 rounded text-emerald-300 text-xs font-mono">$1</code>');
}

export default function ChatWindow() {
  const [messages, setMessages] = useState([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef(null);

  // Typewriter queue refs
  const targetBufferRef = useRef('');
  const displayedLengthRef = useRef(0);
  const tickerIntervalRef = useRef(null);
  const streamDoneDataRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const stopTypewriter = () => {
    if (tickerIntervalRef.current) {
      clearInterval(tickerIntervalRef.current);
      tickerIntervalRef.current = null;
    }
  };

  const startTypewriter = (botMsgId) => {
    stopTypewriter();

    tickerIntervalRef.current = setInterval(() => {
      const targetText = targetBufferRef.current;
      const currentLen = displayedLengthRef.current;
      const remainingLen = targetText.length - currentLen;

      if (remainingLen > 0) {
        // Step dynamically based on buffer size so we never lag excessively behind fast APIs,
        // but maintain a buttery-smooth word/character cadence (~2-4 chars per 18ms tick)
        let step = 2;
        if (remainingLen > 100) step = 7;
        else if (remainingLen > 50) step = 4;
        else if (remainingLen > 20) step = 3;

        const nextLen = Math.min(targetText.length, currentLen + step);
        displayedLengthRef.current = nextLen;
        const newSlice = targetText.slice(0, nextLen);

        setMessages((prevMessages) =>
          prevMessages.map((msg) =>
            msg.id === botMsgId
              ? { ...msg, text: newSlice }
              : msg
          )
        );
      } else if (streamDoneDataRef.current !== null) {
        // Finished typing all text AND done signal was received
        stopTypewriter();
        const doneData = streamDoneDataRef.current;
        setMessages((prevMessages) =>
          prevMessages.map((msg) =>
            msg.id === botMsgId
              ? {
                  ...msg,
                  text: targetText,
                  sources: doneData.sources || [],
                  responseTimeMs: doneData.response_time_ms,
                  isStreaming: false
                }
              : msg
          )
        );
        setIsLoading(false);
      }
    }, 18); // 18ms per tick = ~55 FPS fluid typewriter animation
  };

  const handleSend = async (queryText) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend || !textToSend.trim() || isLoading) return;

    const userMsgId = Date.now().toString();
    const botMsgId = (Date.now() + 1).toString();

    const userMessage = {
      id: userMsgId,
      sender: 'user',
      text: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const initialBotMessage = {
      id: botMsgId,
      sender: 'bot',
      text: '',
      sources: [],
      isStreaming: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMessage, initialBotMessage]);
    if (!queryText) setInputQuery('');
    setIsLoading(true);

    targetBufferRef.current = '';
    displayedLengthRef.current = 0;
    streamDoneDataRef.current = null;

    try {
      await streamQuery(
        textToSend.trim(),
        (chunkText) => {
          targetBufferRef.current += chunkText;
          if (!tickerIntervalRef.current) {
            startTypewriter(botMsgId);
          }
        },
        (doneData) => {
          streamDoneDataRef.current = doneData;
          if (!tickerIntervalRef.current) {
            startTypewriter(botMsgId);
          }
        },
        async (error) => {
          console.warn('Streaming query failed, falling back to direct API endpoint...', error);
          try {
            const fallbackResult = await sendQuery(textToSend.trim());
            stopTypewriter();
            setMessages((prevMessages) =>
              prevMessages.map((msg) =>
                msg.id === botMsgId
                  ? {
                      ...msg,
                      text: fallbackResult.answer || '',
                      sources: fallbackResult.sources || [],
                      responseTimeMs: fallbackResult.response_time_ms,
                      isStreaming: false,
                      isError: false
                    }
                  : msg
              )
            );
            setIsLoading(false);
          } catch (fallbackError) {
            stopTypewriter();
            setMessages((prevMessages) =>
              prevMessages.map((msg) =>
                msg.id === botMsgId
                  ? {
                      ...msg,
                      isError: true,
                      isStreaming: false,
                      text: `Unable to get advisory response: ${fallbackError.message || error.message || 'Server error. Please ensure backend is running.'}`
                    }
                  : msg
              )
            );
            setIsLoading(false);
          }
        }
      );
    } catch (error) {
      stopTypewriter();
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950/40 rounded-2xl border border-emerald-900/40 shadow-2xl backdrop-blur-sm overflow-hidden">
      {/* Top Bar / Advisory Banner (shrink-0) */}
      <div className="shrink-0 bg-emerald-950/80 px-6 py-4 border-b border-emerald-800/40 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-600/20 rounded-xl border border-emerald-500/30 text-emerald-400">
            <Sprout className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-semibold text-emerald-100 text-base">Crop Advisory Chat</h2>
            <p className="text-xs text-emerald-400/80">PAU Package of Practices Knowledge Base</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
          <span className="text-xs text-emerald-300 font-medium hidden sm:inline">RAG Engine Ready</span>
        </div>
      </div>

      {/* Message History List or Centered Welcome Placeholder (flex-1 overflow-y-auto min-h-0) */}
      <div className="flex-1 overflow-y-auto min-h-0 p-4 md:p-6 flex flex-col">
        {messages.length === 0 ? (
          <div className="my-auto flex flex-col items-center justify-center text-center p-4">
            <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-emerald-500/20 to-emerald-800/30 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-4 shadow-xl shadow-emerald-900/30 animate-pulse">
              <Sprout className="w-9 h-9" />
            </div>
            <h3 className="text-xl md:text-2xl font-bold text-white mb-2 tracking-tight">
              Ask me anything about crops, pests, or sowing times
            </h3>
            <p className="text-sm text-emerald-300/80 max-w-md mb-8 leading-relaxed">
              Get warm, expert agricultural advice grounded directly in official PAU Package of Practices advisories.
            </p>

            <div className="w-full max-w-xl">
              <p className="text-xs font-semibold text-emerald-400/80 uppercase tracking-wider mb-3 flex items-center justify-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                Popular Questions
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {SUGGESTED_QUERIES.map((sq, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(sq)}
                    disabled={isLoading}
                    className="text-xs text-left bg-emerald-950/60 hover:bg-emerald-900/80 text-emerald-200 border border-emerald-800/50 hover:border-emerald-500/60 p-3 rounded-xl transition-all shadow-sm hover:shadow-emerald-950/50 flex items-center justify-between group"
                  >
                    <span>{sq}</span>
                    <span className="text-emerald-500 group-hover:translate-x-0.5 transition-transform">→</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex items-start gap-3 md:gap-4 ${
                  msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'
                }`}
              >
                {/* Avatar */}
                <div
                  className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-lg ${
                    msg.sender === 'user'
                      ? 'bg-emerald-600 text-white shadow-emerald-600/20'
                      : msg.isError
                      ? 'bg-rose-900/80 text-rose-300 border border-rose-700/50'
                      : 'bg-emerald-900/90 text-emerald-300 border border-emerald-700/50'
                  }`}
                >
                  {msg.sender === 'user' ? (
                    <User className="w-5 h-5" />
                  ) : msg.isError ? (
                    <AlertTriangle className="w-5 h-5" />
                  ) : (
                    <Bot className="w-5 h-5" />
                  )}
                </div>

                {/* Bubble */}
                <div
                  className={`max-w-[85%] sm:max-w-[78%] rounded-2xl p-4 md:p-5 shadow-md border transition-all ${
                    msg.sender === 'user'
                      ? 'bg-emerald-700/90 text-white border-emerald-600/60 rounded-tr-none'
                      : msg.isError
                      ? 'bg-rose-950/60 border-rose-800/60 text-rose-200 rounded-tl-none'
                      : 'bg-emerald-950/60 border-emerald-800/40 text-emerald-100 rounded-tl-none backdrop-blur-md'
                  }`}
                >
                  {/* Message Content */}
                  {msg.sender === 'user' ? (
                    <p className="text-sm md:text-base whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                  ) : (
                    <FormattedText text={msg.text} isStreaming={msg.isStreaming} />
                  )}

                  {/* Response Footer: Sources & Timing */}
                  {msg.sender === 'bot' && !msg.isError && !msg.isStreaming && (
                    <div className="mt-4 pt-3 border-t border-emerald-900/50 flex flex-wrap items-center justify-between gap-3 text-xs">
                      {/* Sources Badges */}
                      {msg.sources && msg.sources.length > 0 ? (
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-emerald-400/90 font-medium flex items-center gap-1">
                            <BookOpen className="w-3.5 h-3.5" />
                            Sources:
                          </span>
                          {msg.sources.map((src, idx) => (
                            <span
                              key={idx}
                              className="bg-emerald-900/80 hover:bg-emerald-800/90 text-emerald-200 border border-emerald-700/50 px-2.5 py-1 rounded-lg text-xs font-mono flex items-center gap-1 transition-colors"
                            >
                              📌 {src.file}, p.{src.page}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-emerald-500/70 italic">No direct advisory page cited</span>
                      )}

                      {/* Latency badge */}
                      {msg.responseTimeMs && (
                        <span className="text-emerald-400/70 flex items-center gap-1 ml-auto font-mono text-xs">
                          <Clock className="w-3 h-3" />
                          {(msg.responseTimeMs / 1000).toFixed(2)}s
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-start gap-3 flex-row">
            <div className="w-9 h-9 rounded-xl bg-emerald-900/90 text-emerald-300 border border-emerald-700/50 flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5 animate-pulse" />
            </div>
            <div className="bg-emerald-950/60 border border-emerald-800/40 rounded-2xl rounded-tl-none p-4 flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-xs text-emerald-300 font-medium">Searching FAISS & Reranking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompt Chips (Only if messages > 0 and < 3) */}
      {messages.length > 0 && messages.length < 3 && (
        <div className="shrink-0 px-4 pt-2 pb-3 bg-emerald-950/40 border-t border-emerald-900/30">
          <p className="text-xs text-emerald-400/80 mb-2 flex items-center gap-1.5 font-medium">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            Try asking:
          </p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_QUERIES.map((sq, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(sq)}
                disabled={isLoading}
                className="text-xs bg-emerald-900/40 hover:bg-emerald-800/60 text-emerald-200 border border-emerald-700/40 px-3 py-1.5 rounded-xl transition-all hover:border-emerald-500 text-left"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Box Bar (shrink-0 pinned to bottom) */}
      <div className="shrink-0 p-4 bg-emerald-950/90 border-t border-emerald-800/40">
        <div className="flex items-center gap-2 bg-slate-900/80 border border-emerald-700/50 rounded-xl p-2 focus-within:border-emerald-400 focus-within:ring-2 focus-within:ring-emerald-500/20 transition-all">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a crop advisory question (e.g. wheat sowing time, cotton pest control)..."
            disabled={isLoading}
            className="flex-1 bg-transparent text-emerald-100 placeholder-emerald-500/70 px-2 py-1 text-sm md:text-base outline-none disabled:opacity-50"
          />
          <button
            onClick={() => handleSend()}
            disabled={!inputQuery.trim() || isLoading}
            className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-900/50 text-white disabled:text-emerald-600/50 p-2.5 rounded-lg transition-all shadow-md shadow-emerald-700/20 disabled:shadow-none shrink-0"
            title="Send query"
          >
            <Send className="w-4 h-4 md:w-5 md:h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
