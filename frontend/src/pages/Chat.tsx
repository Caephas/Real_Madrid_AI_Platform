import { useState, useRef, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '@/api/client';
import { ChatMessage, ChatMessageData, TypingIndicator } from '@/components/ChatMessage';
import { Send, RotateCcw } from 'lucide-react';

const SUGGESTED_PROMPTS = [
  "Who are we playing next and what are our chances?",
  "Show me the latest transfer news",
  "How are we doing in the current match?",
  "What's our recent form?",
];

const CONVERSATION_KEY = 'rm_chat_conversation_id';

export default function Chat() {
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<ChatMessageData[]>([
    {
      id: 'system-1',
      role: 'system',
      content: "I'm the Real Madrid AI Assistant. I can predict match outcomes, fetch live commentary, and find news for you — and I remember this conversation.",
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const initialPromptSent = useRef(false);
  const conversationIdRef = useRef<string | null>(localStorage.getItem(CONVERSATION_KEY));

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages, loading]);

  // Restore previous conversation
  useEffect(() => {
    const id = conversationIdRef.current;
    if (!id) return;
    api.getConversation(id)
      .then((data) => {
        if (!data.messages.length) return;
        setMessages((prev) => [
          ...prev,
          ...data.messages.map((m, i) => ({
            id: `history-${i}-${m.created_at ?? ''}`,
            role: m.role as 'user' | 'assistant',
            content: m.content,
          })),
        ]);
      })
      .catch(() => {
        // Stale conversation — start fresh
        conversationIdRef.current = null;
        localStorage.removeItem(CONVERSATION_KEY);
      });
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: ChatMessageData = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text.trim(),
    };
    const assistantId = `assistant-${Date.now()}`;
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    // Stream the assistant response into a live-updating bubble
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: 'assistant', content: '', tools_used: [] },
    ]);
    setStreamingId(assistantId);

    try {
      await api.streamChat(
        text.trim(),
        conversationIdRef.current ?? undefined,
        {
          onDelta: (content) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + content } : m))
            );
          },
          onTool: (name) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, tools_used: [...(m.tools_used ?? []), name] }
                  : m
              )
            );
          },
          onDone: (conversationId) => {
            conversationIdRef.current = conversationId;
            localStorage.setItem(CONVERSATION_KEY, conversationId);
          },
          onError: (message) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content || `⚠️ ${message}` }
                  : m
              )
            );
          },
        }
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: m.content || "Sorry, I couldn't process your request. The backend may be unavailable." }
            : m
        )
      );
    } finally {
      setLoading(false);
      setStreamingId(null);
    }
  }, [loading]);

  const newConversation = useCallback(() => {
    conversationIdRef.current = null;
    localStorage.removeItem(CONVERSATION_KEY);
    setMessages([{
      id: 'system-1',
      role: 'system',
      content: "I'm the Real Madrid AI Assistant. I can predict match outcomes, fetch live commentary, and find news for you — and I remember this conversation.",
    }]);
    inputRef.current?.focus();
  }, []);

  // Handle pre-filled prompt from URL
  useEffect(() => {
    const prompt = searchParams.get('prompt');
    if (prompt && !initialPromptSent.current) {
      initialPromptSent.current = true;
      sendMessage(prompt);
    }
  }, [searchParams, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const hasUserMessages = messages.some((m) => m.role === 'user');

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)] animate-fade-in-up">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-4 pb-4">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {loading && !streamingId && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Suggested prompts */}
      {!hasUserMessages && (
        <div className="flex flex-wrap gap-2 pb-3">
          {SUGGESTED_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => sendMessage(prompt)}
              className="text-xs px-3 py-1.5 rounded-full bg-muted/50 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-colors border border-border"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="glass-card-static p-3 flex gap-2 items-end">
        {hasUserMessages && (
          <button
            onClick={newConversation}
            disabled={loading}
            title="Start a new conversation"
            className="text-xs text-muted-foreground hover:text-primary disabled:opacity-40 px-2 py-1.5 rounded-lg hover:bg-muted/20 transition-colors flex items-center gap-1"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            New
          </button>
        )}
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask me anything about Real Madrid..."
          rows={1}
          className="flex-1 bg-transparent resize-none text-sm text-foreground placeholder:text-muted-foreground focus:outline-none max-h-32"
          disabled={loading}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
          className="bg-primary text-primary-foreground rounded-lg p-2.5 hover:bg-primary/90 transition-colors disabled:opacity-40"
          aria-label="Send message"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
