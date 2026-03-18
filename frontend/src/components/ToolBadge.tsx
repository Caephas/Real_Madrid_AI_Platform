import { cn } from '@/lib/utils';

interface ToolBadgeProps {
  tools: string[];
  className?: string;
}

export function ToolBadge({ tools, className }: ToolBadgeProps) {
  if (!tools.length) return null;
  return (
    <div className={cn('flex flex-wrap gap-1.5 mt-2', className)}>
      <span className="text-xs text-muted-foreground">Used:</span>
      {tools.map((tool) => (
        <span
          key={tool}
          className="font-data text-xs px-2 py-0.5 rounded bg-muted/50 text-muted-foreground"
        >
          {tool}
        </span>
      ))}
    </div>
  );
}
