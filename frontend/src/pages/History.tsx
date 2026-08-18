import { useState } from 'react';
import { api, SeasonMatch } from '@/api/client';
import { useApi } from '@/hooks/useApi';
import { StandingsTable } from '@/components/StandingsTable';
import { CardSkeleton, LoadingSkeleton } from '@/components/LoadingSkeleton';
import { ErrorBanner } from '@/components/ErrorBanner';
import FilterTable from '@/components/ai/FilterTable';
import { CalendarRange } from 'lucide-react';

function formatDate(d: string) {
  return new Date(d + 'T00:00:00').toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

function seasonLabel(season: number) {
  return `${season}/${String(season + 1).slice(2)}`;
}

export default function History() {
  const [season, setSeason] = useState<number | undefined>(undefined);
  const history = useApi(() => api.getHistory(season), [season]);
  const standings = useApi(() => api.getStandings(season), [season]);
  const matches = history.data?.matches ?? [];
  const seasons = history.data?.available_seasons ?? [];

  const summary = matches.reduce(
    (acc, m) => {
      acc[m.result] += 1;
      acc.gf += m.gf;
      acc.ga += m.ga;
      return acc;
    },
    { W: 0, D: 0, L: 0, gf: 0, ga: 0 } as Record<string, number>
  );
  const points = summary.W * 3 + summary.D;

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight">Season History</h1>
            <span className="text-xs font-semibold text-primary bg-primary/10 border border-primary/20 rounded-full px-2.5 py-1">
              {history.data?.season != null ? seasonLabel(history.data.season) : ''}
            </span>
          </div>
          <p className="text-muted-foreground mt-1">Real Madrid results across La Liga seasons</p>
        </div>

        {/* Season picker */}
        <div className="flex items-center gap-2">
          <CalendarRange className="w-4 h-4 text-muted-foreground" />
          <select
            value={history.data?.season ?? ''}
            onChange={(e) => setSeason(e.target.value ? Number(e.target.value) : undefined)}
            className="bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">Latest</option>
            {seasons.map((s) => (
              <option key={s} value={s}>{seasonLabel(s)}</option>
            ))}
          </select>
        </div>
      </div>

      {(history.error || standings.error) && (
        <ErrorBanner message="Could not load season data" onRetry={() => { history.refetch(); standings.refetch(); }} />
      )}

      {/* Season summary */}
      {!history.loading && matches.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
          {[
            { label: 'Played', value: matches.length },
            { label: 'Won', value: summary.W },
            { label: 'Drawn', value: summary.D },
            { label: 'Lost', value: summary.L },
            { label: 'Goals', value: `${summary.gf} – ${summary.ga}` },
            { label: 'Points', value: points },
          ].map((item) => (
            <div key={item.label} className="glass-card-static p-4 text-center">
              <p className="text-2xl font-bold font-data text-primary">{item.value}</p>
              <p className="text-[11px] text-muted-foreground uppercase tracking-wider mt-1">{item.label}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Match list */}
        <div className="glass-card-static overflow-hidden">
          <div className="px-5 py-3.5 border-b border-border/50">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Matches</h2>
          </div>
          <div className="p-4">
          {history.loading && !matches.length ? (
            <div className="p-4"><LoadingSkeleton lines={8} /></div>
          ) : matches.length ? (
            <FilterTable
              rows={matches.map((m: SeasonMatch) => ({
                task: m.opponent,
                date: formatDate(m.date),
                status: m.result === 'W' ? 'done' : m.result === 'D' ? 'progress' : 'todo',
                owner: `${m.venue} · ${m.gf}–${m.ga}`,
              }))}
              filterLabels={{ done: 'Wins', progress: 'Draws', todo: 'Losses' }}
              headers={['Opponent', 'Date', 'Result', 'Venue · Score']}
            />
          ) : (
            <p className="p-5 text-sm text-muted-foreground">No matches for this season</p>
          )}
          </div>
        </div>

        {/* Standings */}
        <div className="glass-card-static divide-y divide-border/50 overflow-hidden">
          <div className="px-5 py-3.5 border-b border-border/50">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Final / Current Table
            </h2>
          </div>
          <div className="p-4">
            {standings.loading && !standings.data?.standings.length ? (
              <LoadingSkeleton lines={8} />
            ) : standings.data?.standings.length ? (
              <StandingsTable standings={standings.data.standings} />
            ) : (
              <p className="text-sm text-muted-foreground">No standings yet</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
