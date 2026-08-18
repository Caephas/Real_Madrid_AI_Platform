import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api, Article, Fixture } from '@/api/client';
import { useApi } from '@/hooks/useApi';
import { useCountdown, fixtureTargetIso } from '@/hooks/useCountdown';
import { PredictionCard } from '@/components/PredictionCard';
import { MatchAnalysis } from '@/components/MatchAnalysis';
import { ArticleReader } from '@/components/ArticleReader';
import { CardSkeleton } from '@/components/LoadingSkeleton';
import { ErrorBanner } from '@/components/ErrorBanner';
import { StandingsTable } from '@/components/StandingsTable';
import LoadingState from '@/components/ai/LoadingState';
import { Send, Radio, Zap, Calendar, Trophy } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PredictionResult {
  win: number;
  draw: number;
  loss: number;
  insights?: string[];
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [quickChat, setQuickChat] = useState('');
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [selected, setSelected] = useState<Fixture | null>(null);
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [predLoading, setPredLoading] = useState(false);
  const [predError, setPredError] = useState<string | null>(null);

  const season = useApi(() => api.getSeason(), []);
  const articles = useApi(() => api.getArticles({ limit: 3 }), []);
  const commentary = useApi(() => api.getCommentary(541), []);
  const results = useApi(() => api.getResults(5), []);
  const standings = useApi(() => api.getStandings(), []);
  const h2h = useApi(
    () => (selected ? api.getH2H(selected.opponent) : Promise.resolve(null)),
    [selected?.opponent]
  );

  const nextMatch = season.data?.next_match ?? null;
  const upcomingFixtures = (season.data?.fixtures ?? []).filter((f) => f.status === 'upcoming');
  const countdown = useCountdown(nextMatch ? fixtureTargetIso(nextMatch) : null);

  // Preselect a match from the Fixtures page (?opponent=&date=)
  useEffect(() => {
    const opponent = searchParams.get('opponent');
    const date = searchParams.get('date');
    if (opponent && date && season.data) {
      const match = season.data.fixtures.find((f) => f.opponent === opponent && f.date === date);
      if (match) {
        setSelected(match);
        setPrediction(null);
      }
    }
  }, [searchParams, season.data]);

  // Auto-predict when a match is selected
  useEffect(() => {
    if (!selected) return;
    setPredLoading(true);
    setPredError(null);
    setPrediction(null);
    api.predict(selected.opponent, selected.venue, selected.date)
      .then(setPrediction)
      .catch((e) => setPredError(e.message))
      .finally(() => setPredLoading(false));
  }, [selected]);

  const selectMatch = (match: Fixture) => {
    setSelected(match);
    setPrediction(null);
    navigate('/', { replace: true });
  };

  const handleQuickChat = (e: React.FormEvent) => {
    e.preventDefault();
    if (quickChat.trim()) navigate(`/chat?prompt=${encodeURIComponent(quickChat)}`);
  };

  const formatDate = (d: string) => {
    const date = new Date(d + 'T00:00:00');
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  };

  const loading = season.loading || predLoading;
  const hasPrediction = prediction && selected;

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* Season header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-3xl font-bold tracking-tight">Match Intelligence</h1>
            <span className="text-xs font-semibold text-primary bg-primary/10 border border-primary/20 rounded-full px-2.5 py-1">
              {season.data?.season ?? '2026/27'} · {season.data?.competition ?? 'La Liga'}
            </span>
          </div>
          <p className="text-muted-foreground mt-1">Real-time predictions, news, and live insights</p>
        </div>
        {nextMatch && !countdown.isPast && (
          <div className="glass-card-static px-5 py-3 text-right">
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Next kickoff</p>
            <p className="text-lg font-bold font-data text-primary">
              {countdown.days}d {countdown.hours}h {countdown.minutes}m {countdown.seconds}s
            </p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Prediction — auto-loaded from selected/next fixture */}
        {loading ? (
          <div className="glass-card p-8 flex items-center justify-center">
            <LoadingState label="Computing prediction" variant="Drive" />
          </div>
        ) : predError ? (
          <ErrorBanner message={predError} onRetry={() => selected && selectMatch(selected)} />
        ) : hasPrediction ? (
          <PredictionCard
            opponent={selected.opponent}
            venue={selected.venue}
            date={selected.date}
            matchday={selected.matchday}
            targetIso={selected.kickoff}
            win={prediction.win}
            draw={prediction.draw}
            loss={prediction.loss}
            insights={prediction.insights}
            h2h={h2h.data}
          />
        ) : (
          <div className="glass-card p-6 text-center text-muted-foreground">
            No upcoming fixtures — check back when the season schedule is live
          </div>
        )}

        {/* Match Analysis */}
        {hasPrediction && (
          <MatchAnalysis
            opponent={selected.opponent}
            venue={selected.venue}
            date={selected.date}
          />
        )}

        {/* Live Match Status */}
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-primary" />
            <h3 className="text-lg font-semibold">Live Match Status</h3>
          </div>
          {commentary.loading ? (
            <CardSkeleton className="!p-0 !border-0 !shadow-none !bg-transparent !backdrop-blur-none" />
          ) : commentary.data?.message ? (
            <div className="text-center py-6">
              <p className="text-muted-foreground">{commentary.data.message}</p>
              {nextMatch && (
                <button
                  onClick={() => selectMatch(nextMatch)}
                  className="mt-4 text-sm text-primary hover:underline"
                >
                  Next: {nextMatch.opponent} ({formatDate(nextMatch.date)}) →
                </button>
              )}
            </div>
          ) : commentary.data && !commentary.data.message ? (
            <div className="text-center space-y-2">
              <p className="text-2xl font-bold font-data">
                {commentary.data.home_team} {commentary.data.score} {commentary.data.away_team}
              </p>
              <div className="flex items-center justify-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="live-pulse absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary" />
                </span>
                <span className="text-sm text-primary font-data">{commentary.data.match_status}</span>
              </div>
            </div>
          ) : (
            <div className="text-center py-6">
              <p className="text-muted-foreground">No live match right now</p>
            </div>
          )}
        </div>

        {/* Upcoming Fixtures */}
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-primary" />
              <h3 className="text-lg font-semibold">Upcoming Fixtures</h3>
            </div>
            <button
              onClick={() => navigate('/fixtures')}
              className="text-xs text-primary hover:underline"
            >
              Full season →
            </button>
          </div>
          {season.loading ? (
            <CardSkeleton className="!p-0 !border-0 !shadow-none !bg-transparent !backdrop-blur-none" />
          ) : upcomingFixtures.length > 0 ? (
            <div className="space-y-2">
              {upcomingFixtures.slice(0, 8).map((fix) => (
                <button
                  key={fix.matchday}
                  onClick={() => selectMatch(fix)}
                  className={cn(
                    'w-full flex items-center justify-between p-3 rounded-lg text-left transition-colors',
                    selected?.matchday === fix.matchday
                      ? 'bg-primary/10 border border-primary/30'
                      : 'bg-muted/20 hover:bg-muted/40'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] font-data text-muted-foreground bg-muted/40 rounded px-1.5 py-0.5">
                      MD{fix.matchday}
                    </span>
                    <div>
                      <p className="text-sm font-medium">{fix.opponent}</p>
                      <p className="text-xs text-muted-foreground">{fix.venue}</p>
                    </div>
                  </div>
                  <span className="text-xs text-muted-foreground font-data">{formatDate(fix.date)}</span>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No upcoming fixtures</p>
          )}
        </div>

        {/* Recent Results */}
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Trophy className="w-4 h-4 text-primary" />
            <h3 className="text-lg font-semibold">Recent Results</h3>
          </div>
          {results.loading ? (
            <CardSkeleton className="!p-0 !border-0 !shadow-none !bg-transparent !backdrop-blur-none" />
          ) : results.data?.results.length ? (
            <div className="space-y-2">
              {results.data.results.map((r) => (
                <div
                  key={r.date + r.opponent}
                  className="flex items-center justify-between p-3 rounded-lg bg-muted/20"
                >
                  <div className="flex items-center gap-2.5">
                    <span className={cn(
                      'w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold font-data',
                      r.result === 'W' && 'bg-win/20 text-win',
                      r.result === 'D' && 'bg-draw/20 text-draw',
                      r.result === 'L' && 'bg-loss/20 text-loss',
                    )}>
                      {r.result}
                    </span>
                    <div>
                      <p className="text-sm font-medium">vs {r.opponent}</p>
                      <p className="text-xs text-muted-foreground">{formatDate(r.date)} · {r.venue}</p>
                    </div>
                  </div>
                  <span className="text-sm font-data font-semibold">{r.score}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No finished matches yet — connect API-Football to see live results
            </p>
          )}
        </div>

        {/* Latest News */}
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            <h3 className="text-lg font-semibold">Latest News</h3>
          </div>
          {articles.loading ? (
            <CardSkeleton className="!p-0 !border-0 !shadow-none !bg-transparent !backdrop-blur-none" />
          ) : articles.error ? (
            <p className="text-sm text-muted-foreground">Could not load articles</p>
          ) : articles.data?.length ? (
            <div className="space-y-3">
              {articles.data.map((a) => (
                <div
                  key={a.article_id}
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedArticle(a)}
                  onKeyDown={(e) => e.key === 'Enter' && setSelectedArticle(a)}
                  className="block p-3 rounded-lg bg-muted/20 hover:bg-muted/40 transition-colors cursor-pointer"
                >
                  <p className="text-sm font-medium text-foreground leading-snug">{a.title}</p>
                  <p className="text-xs text-muted-foreground mt-1">{a.category}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No articles found</p>
          )}
        </div>
      </div>

      {/* La Liga Standings */}
      <div className="glass-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Trophy className="w-4 h-4 text-primary" />
            <h3 className="text-lg font-semibold">
              La Liga Standings{' '}
              <span className="text-xs text-muted-foreground font-normal">
                {standings.data?.season ? `${standings.data.season}/${standings.data.season + 1}` : ''}
              </span>
            </h3>
          </div>
          <button onClick={() => navigate('/history')} className="text-xs text-primary hover:underline">
            Season history →
          </button>
        </div>
        {standings.loading ? (
          <CardSkeleton className="!p-0 !border-0 !shadow-none !bg-transparent !backdrop-blur-none" />
        ) : standings.data?.standings.length ? (
          <StandingsTable standings={standings.data.standings} />
        ) : (
          <p className="text-sm text-muted-foreground">No standings available yet</p>
        )}
      </div>

      {/* Quick Chat — full width */}
      <div className="glass-card p-6 space-y-4">
        <h3 className="text-lg font-semibold">Ask the Agent</h3>
        <form onSubmit={handleQuickChat} className="flex gap-2">
          <input
            type="text"
            value={quickChat}
            onChange={(e) => setQuickChat(e.target.value)}
            placeholder="Ask about Real Madrid, predictions, or news..."
            className="flex-1 bg-muted/30 border border-border rounded-lg px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <button
            type="submit"
            className="bg-primary text-primary-foreground rounded-lg px-4 py-2.5 hover:bg-primary/90 transition-colors"
            aria-label="Send"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

      {selectedArticle && (
        <ArticleReader article={selectedArticle} onClose={() => setSelectedArticle(null)} />
      )}
    </div>
  );
}
