// File: frontend/src/pages/Dashboard.tsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, Article } from '@/api/client';
import { useApi } from '@/hooks/useApi';
import { PredictionCard } from '@/components/PredictionCard';
import { ArticleReader } from '@/components/ArticleReader';
import { CardSkeleton } from '@/components/LoadingSkeleton';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Send, Radio, Zap, Calendar } from 'lucide-react';

interface MatchInfo {
  opponent: string;
  venue: string;
  date: string;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [quickChat, setQuickChat] = useState('');
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  // Fixture + prediction state
  const [nextMatch, setNextMatch] = useState<MatchInfo | null>(null);
  const [upcomingFixtures, setUpcomingFixtures] = useState<MatchInfo[]>([]);
  const [fixtureLoading, setFixtureLoading] = useState(true);
  const [prediction, setPrediction] = useState<{ win: number; draw: number; loss: number } | null>(null);
  const [predLoading, setPredLoading] = useState(false);
  const [predError, setPredError] = useState<string | null>(null);

  const articles = useApi(() => api.getArticles({ limit: 3 }), []);
  const commentary = useApi(() => api.getCommentary(541), []);

  // Fetch next match + all remaining fixtures
  useEffect(() => {
    setFixtureLoading(true);
    Promise.all([
      fetch('/next-match').then((r) => r.json()),
      fetch('/fixtures').then((r) => r.json()),
    ])
      .then(([next, all]) => {
        if (next && next.opponent) {
          setNextMatch(next);
        }
        if (all && all.fixtures) {
          setUpcomingFixtures(all.fixtures);
        }
      })
      .catch(() => {})
      .finally(() => setFixtureLoading(false));
  }, []);

  // Auto-predict when nextMatch is set
  useEffect(() => {
    if (!nextMatch) return;
    setPredLoading(true);
    setPredError(null);
    api.predict(nextMatch.opponent, nextMatch.venue, nextMatch.date)
      .then(setPrediction)
      .catch((e) => setPredError(e.message))
      .finally(() => setPredLoading(false));
  }, [nextMatch]);

  const predictMatch = (match: MatchInfo) => {
    setNextMatch(match);
    setPrediction(null);
  };

  const handleQuickChat = (e: React.FormEvent) => {
    e.preventDefault();
    if (quickChat.trim()) navigate(`/chat?prompt=${encodeURIComponent(quickChat)}`);
  };

  const formatDate = (d: string) => {
    const date = new Date(d + 'T00:00:00');
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  };

  return (
    <div className="space-y-8 animate-fade-in-up">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Match Intelligence</h1>
        <p className="text-muted-foreground mt-1">Real-time predictions, news, and live insights</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Prediction — auto-loaded from next fixture */}
        {fixtureLoading || predLoading ? (
          <CardSkeleton />
        ) : predError ? (
          <ErrorBanner message="Could not load prediction" onRetry={() => window.location.reload()} />
        ) : prediction && nextMatch ? (
          <PredictionCard
            opponent={nextMatch.opponent}
            venue={nextMatch.venue}
            date={nextMatch.date}
            win={prediction.win}
            draw={prediction.draw}
            loss={prediction.loss}
          />
        ) : (
          <div className="glass-card p-6 text-center text-muted-foreground">
            No upcoming fixtures
          </div>
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
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-primary" />
            <h3 className="text-lg font-semibold">Upcoming Fixtures</h3>
          </div>
          {fixtureLoading ? (
            <CardSkeleton className="!p-0 !border-0 !shadow-none !bg-transparent !backdrop-blur-none" />
          ) : upcomingFixtures.length > 0 ? (
            <div className="space-y-2">
              {upcomingFixtures.map((fix) => (
                <button
                  key={fix.date + fix.opponent}
                  onClick={() => predictMatch(fix)}
                  className={`w-full flex items-center justify-between p-3 rounded-lg text-left transition-colors ${
                    nextMatch?.date === fix.date && nextMatch?.opponent === fix.opponent
                      ? 'bg-primary/10 border border-primary/30'
                      : 'bg-muted/20 hover:bg-muted/40'
                  }`}
                >
                  <div>
                    <p className="text-sm font-medium">{fix.opponent}</p>
                    <p className="text-xs text-muted-foreground">{fix.venue}</p>
                  </div>
                  <span className="text-xs text-muted-foreground font-data">{formatDate(fix.date)}</span>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No upcoming fixtures</p>
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
