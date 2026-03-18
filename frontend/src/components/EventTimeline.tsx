import { MatchEvent } from '@/api/client';
import { cn } from '@/lib/utils';

const eventIcons: Record<string, string> = {
  'Goal': '⚽',
  'Card': '🟨',
  'Red Card': '🟥',
  'Yellow Card': '🟨',
  'Substitution': '🔄',
};

interface EventTimelineProps {
  events: MatchEvent[];
  className?: string;
}

export function EventTimeline({ events, className }: EventTimelineProps) {
  if (!events.length) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p className="text-lg">No events yet</p>
        <p className="text-sm mt-1">Waiting for the match to begin...</p>
      </div>
    );
  }

  return (
    <div className={cn('relative', className)}>
      {/* Vertical line */}
      <div className="absolute left-6 top-0 bottom-0 w-px bg-border" />

      <div className="space-y-4">
        {events.map((event, i) => {
          const isGoal = event.type === 'Goal';
          return (
            <div
              key={`${event.minute}-${i}`}
              className={cn(
                'relative pl-14 animate-fade-in-up',
              )}
              style={{ animationDelay: `${i * 80}ms` }}
            >
              {/* Node */}
              <div className={cn(
                'absolute left-4 w-5 h-5 rounded-full flex items-center justify-center text-xs',
                isGoal ? 'bg-primary shadow-[0_0_12px_hsl(var(--gold)/0.4)]' : 'bg-muted'
              )}>
                {eventIcons[event.type] || '📋'}
              </div>

              <div className={cn(
                'glass-card-static p-4',
                isGoal && 'border-gold'
              )}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-data text-sm text-primary font-bold">{event.minute}'</span>
                  <span className="text-sm font-medium">{event.player}</span>
                </div>
                <p className="text-sm text-muted-foreground">{event.commentary}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
