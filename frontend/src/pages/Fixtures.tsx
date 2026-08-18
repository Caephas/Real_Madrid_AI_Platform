import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, Fixture } from '@/api/client';
import { useApi } from '@/hooks/useApi';
import { useCountdown, fixtureTargetIso } from '@/hooks/useCountdown';
import { CardSkeleton } from '@/components/LoadingSkeleton';
import { ErrorBanner } from '@/components/ErrorBanner';
import { CalendarDays, Home, Plane, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

const RESULT_STYLES: Record<string, string> = {
  W: 'bg-win/20 text-win',
  D: 'bg-draw/20 text-draw',
  L: 'bg-loss/20 text-loss',
};

function formatDate(d: string) {
  return new Date(d + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
  });
}

function kickoffTime(fixture: Fixture) {
  if (!fixture.kickoff) return null;
  return new Date(fixture.kickoff).toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit',
  });
}

export default function Fixtures() {
  const navigate = useNavigate();
  const season = useApi(() => api.getSeason(), []);
  const nextMatch = season.data?.next_match ?? null;
  const countdown = useCountdown(nextMatch ? fixtureTargetIso(nextMatch) : null);

  const grouped = useMemo(() => {
    const byMonth = new Map<string, Fixture[]>();
    for (const fixture of season.data?.fixtures ?? []) {
      const month = new Date(fixture.date + 'T00:00:00').toLocaleDateString('en-US', {
        month: 'long', year: 'numeric',
      });
      byMonth.set(month, [...(byMonth.get(month) ?? []), fixture]);
    }
    return [...byMonth.entries()];
  }, [season.data]);

  const openMatch = (fixture: Fixture) => {
    if (fixture.status === 'upcoming') {
      navigate(`/?opponent=${encodeURIComponent(fixture.opponent)}&date=${fixture.date}`);
    }
  };

  if (season.loading && !season.data) {
    return (
      <div className="space-y-6 animate-fade-in-up">
        <h1 className="text-3xl font-bold tracking-tight">2026/27 Fixtures</h1>
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight">Season Fixtures</h1>
            <span className="text-xs font-semibold text-primary bg-primary/10 border border-primary/20 rounded-full px-2.5 py-1">
              {season.data?.season ?? '2026/27'} · {season.data?.competition ?? 'La Liga'}
            </span>
          </div>
          <p className="text-muted-foreground mt-1">
            {season.data?.start_date ?? ''} → {season.data?.end_date ?? ''} · 38 matchdays
          </p>
        </div>
      </div>

      {season.error && <ErrorBanner message="Could not load fixtures" onRetry={season.refetch} />}

      {/* Next-up hero */}
      {nextMatch && (
        <button
          onClick={() => openMatch(nextMatch)}
          className="glass-card w-full p-6 text-left hover:border-primary/40 transition-colors"
        >
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="space-y-1.5">
              <p className="text-[11px] text-primary uppercase tracking-wider font-semibold flex items-center gap-1.5">
                <CalendarDays className="w-3.5 h-3.5" /> Next up · Matchday {nextMatch.matchday}
              </p>
              <p className="text-2xl font-bold">
                Real Madrid <span className="text-muted-foreground font-normal">vs</span> {nextMatch.opponent}
              </p>
              <p className="text-sm text-muted-foreground flex items-center gap-2">
                {nextMatch.venue === 'Home' ? <Home className="w-3.5 h-3.5" /> : <Plane className="w-3.5 h-3.5" />}
                {formatDate(nextMatch.date)} · {nextMatch.venue}
                {nextMatch.kickoff && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" /> {kickoffTime(nextMatch)}
                  </span>
                )}
              </p>
            </div>
            {!countdown.isPast && (
              <div className="text-right">
                <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Kickoff in</p>
                <p className="text-2xl font-bold font-data text-primary">
                  {countdown.days}d {countdown.hours}h {countdown.minutes}m {countdown.seconds}s
                </p>
                <p className="text-xs text-primary mt-1">Get prediction →</p>
              </div>
            )}
          </div>
        </button>
      )}

      {/* Full season by month */}
      {grouped.map(([month, fixtures]) => (
        <div key={month} className="space-y-2">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider pt-2">
            {month}
          </h2>
          <div className="glass-card-static divide-y divide-border/50 overflow-hidden">
            {fixtures.map((fixture) => {
              const finished = fixture.status === 'finished';
              return (
                <button
                  key={fixture.matchday}
                  onClick={() => openMatch(fixture)}
                  disabled={finished}
                  className={cn(
                    'w-full flex items-center justify-between gap-3 px-5 py-3.5 text-left transition-colors',
                    finished
                      ? 'cursor-default opacity-80'
                      : 'hover:bg-muted/20 cursor-pointer'
                  )}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-[10px] font-data text-muted-foreground bg-muted/40 rounded px-1.5 py-0.5 w-10 text-center">
                      MD{fixture.matchday}
                    </span>
                    <span className={cn(
                      'w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0',
                      fixture.venue === 'Home'
                        ? 'bg-primary/10 text-primary'
                        : 'bg-muted/40 text-muted-foreground'
                    )}>
                      {fixture.venue === 'Home' ? <Home className="w-3.5 h-3.5" /> : <Plane className="w-3.5 h-3.5" />}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{fixture.opponent || 'TBC'}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(fixture.date)}
                        {fixture.kickoff && ` · ${kickoffTime(fixture)}`}
                      </p>
                    </div>
                  </div>

                  {finished ? (
                    <div className="flex items-center gap-2">
                      {fixture.result && (
                        <span className={cn(
                          'w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold font-data',
                          RESULT_STYLES[fixture.result],
                        )}>
                          {fixture.result}
                        </span>
                      )}
                      <span className="text-sm font-data font-semibold">{fixture.score ?? '–'}</span>
                    </div>
                  ) : (
                    <span className="text-[11px] font-medium text-primary bg-primary/10 rounded-full px-2.5 py-1">
                      Upcoming
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
