import ReactMarkdown from 'react-markdown';
import { ToolBadge } from './ToolBadge';
import { cn } from '@/lib/utils';

export interface ChatMessageData {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tools_used?: string[];
}

interface ChatMessageProps {
  message: ChatMessageData;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="text-center py-4 px-6">
        <p className="text-sm text-muted-foreground italic">{message.content}</p>
      </div>
    );
  }

  return (
    <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn(
        'max-w-[80%] rounded-2xl px-5 py-3',
        isUser
          ? 'bg-secondary text-secondary-foreground rounded-br-sm border border-primary/20'
          : 'glass-card-static text-foreground rounded-bl-sm'
      )}>
        <div className="prose prose-invert prose-sm max-w-none [&_p]:mb-2 [&_p:last-child]:mb-0 [&_code]:font-mono [&_code]:text-primary [&_code]:bg-muted/50 [&_code]:px-1 [&_code]:rounded">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
        {message.tools_used && <ToolBadge tools={message.tools_used} />}
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="glass-card-static rounded-2xl rounded-bl-sm px-5 py-4">
        <div className="flex gap-1.5">
          <div className="typing-dot" />
          <div className="typing-dot" />
          <div className="typing-dot" />
        </div>
      </div>
    </div>
  );
}
