import { AnimatedCounter } from './AnimatedCounter';
import { useCountdown } from '@/hooks/useCountdown';
import { H2HRecord } from '@/api/client';
import { cn } from '@/lib/utils';

interface PredictionCardProps {
  opponent: string;
  venue: string;
  date: string;
  matchday?: number;
  targetIso?: string | null;
  win: number;
  draw: number;
  loss: number;
  insights?: string[];
  h2h?: H2HRecord | null;
  className?: string;
}

export function PredictionCard({
  opponent, venue, date, matchday, targetIso, win, draw, loss, insights, h2h, className,
}: PredictionCardProps) {
  const winPct = Math.round(win * 100);
  const drawPct = Math.round(draw * 100);
  const lossPct = Math.round(loss * 100);
  const countdown = useCountdown(targetIso);

  return (
    <div className={cn('glass-card p-6 space-y-5', className)}>
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-lg font-semibold text-foreground">Match Prediction</h3>
        <div className="flex items-center gap-2">
          {matchday && (
            <span className="text-[11px] font-medium text-primary bg-primary/10 border border-primary/20 rounded-full px-2 py-0.5">
              MD {matchday}
            </span>
          )}
          <span className="text-xs text-muted-foreground font-data">{date}</span>
        </div>
      </div>

      {targetIso && !countdown.isPast && (
        <div className="text-center">
          <span className="text-xs text-muted-foreground uppercase tracking-wider">Kickoff in</span>
          <p className="text-xl font-bold font-data text-primary mt-0.5">
            {countdown.days}d {countdown.hours}h {countdown.minutes}m {countdown.seconds}s
          </p>
        </div>
      )}

      <div className="text-center space-y-1">
        <p className="text-sm text-muted-foreground uppercase tracking-wider">
          {venue.toLowerCase() === 'home' ? 'Home' : 'Away'}
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

      {/* Head-to-head */}
      {h2h && h2h.meetings > 0 && (
        <div className="pt-1">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wider mb-1.5">
            Head to head · {h2h.meetings} meetings
          </p>
          <div className="flex items-center gap-1.5 text-xs font-data">
            <span className="px-2 py-1 rounded bg-win/15 text-win font-semibold">{h2h.rm_wins}W</span>
            <span className="px-2 py-1 rounded bg-draw/15 text-draw font-semibold">{h2h.draws}D</span>
            <span className="px-2 py-1 rounded bg-loss/15 text-loss font-semibold">{h2h.opponent_wins}L</span>
            <span className="ml-auto text-muted-foreground">
              {h2h.rm_goals} – {h2h.opponent_goals} goals
            </span>
          </div>
        </div>
      )}

      {/* Model insights */}
      {insights && insights.length > 0 && (
        <div className="pt-1 space-y-1.5">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Why the model leans this way</p>
          {insights.map((insight, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-foreground/85">
              <span className="w-1 h-1 rounded-full bg-primary mt-1.5 flex-shrink-0" />
              <span>{insight}</span>
            </div>
          ))}
        </div>
      )}
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
