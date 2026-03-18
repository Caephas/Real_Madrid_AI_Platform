import { AnimatedCounter } from './AnimatedCounter';
import { cn } from '@/lib/utils';

interface PredictionCardProps {
  opponent: string;
  venue: string;
  date: string;
  win: number;
  draw: number;
  loss: number;
  className?: string;
}

export function PredictionCard({ opponent, venue, date, win, draw, loss, className }: PredictionCardProps) {
  const winPct = Math.round(win * 100);
  const drawPct = Math.round(draw * 100);
  const lossPct = Math.round(loss * 100);

  return (
    <div className={cn('glass-card p-6 space-y-5', className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground">Match Prediction</h3>
        <span className="text-xs text-muted-foreground font-data">{date}</span>
      </div>

      <div className="text-center space-y-1">
        <p className="text-sm text-muted-foreground uppercase tracking-wider">
          {venue === 'home' ? 'Home' : 'Away'}
        </p>
        <p className="text-xl font-bold">
          Real Madrid <span className="text-muted-foreground mx-2">vs</span> {opponent}
        </p>
      </div>

      <div className="space-y-3">
        <ProbabilityBar label="Win" value={winPct} total={100} colorClass="bg-win" textClass="text-win" />
        <ProbabilityBar label="Draw" value={drawPct} total={100} colorClass="bg-draw" textClass="text-draw" />
        <ProbabilityBar label="Loss" value={lossPct} total={100} colorClass="bg-loss" textClass="text-loss" />
      </div>
    </div>
  );
}

function ProbabilityBar({ label, value, total, colorClass, textClass }: {
  label: string; value: number; total: number; colorClass: string; textClass: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className={cn('font-data font-semibold', textClass)}>
          <AnimatedCounter value={value} suffix="%" />
        </span>
      </div>
      <div className="h-2 rounded-full bg-muted/30 overflow-hidden">
        <div
          className={cn('prediction-bar', colorClass)}
          style={{ width: `${(value / total) * 100}%`, animation: 'bar-grow 1s var(--ease-out) both' }}
        />
      </div>
    </div>
  );
}
