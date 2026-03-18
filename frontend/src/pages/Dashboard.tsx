// File: frontend/src/pages/Dashboard.tsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, NextFixture } from '@/api/client';
import { useApi } from '@/hooks/useApi';
import { PredictionCard } from '@/components/PredictionCard';
import { ArticleCard } from '@/components/ArticleCard';
import { ArticleReader } from '@/components/ArticleReader';
import { CardSkeleton } from '@/components/LoadingSkeleton';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Send, Radio, Zap } from 'lucide-react';
import { Article } from '@/api/client';

interface MatchInput {
  opponent: string;
  venue: string;
  date: string;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [quickChat, setQuickChat] = useState('');
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  // Next fixture state
  const [matchInput, setMatchInput] = useState<MatchInput | null>(null);
  const [fixtureLoading, setFixtureLoading] = useState(true);
  const [useManualForm, setUseManualForm] = useState(false);
  const [manualOpponent, setManualOpponent] = useState('Barcelona');
  const [manualVenue, setManualVenue] = useState('Home');
  const [manualDate, setManualDate] = useState(new Date().toISOString().slice(0, 10));

  // Prediction state
  const [prediction, setPrediction] = useState<{ win: number; draw: number; loss: number } | null>(null);
  const [predLoading, setPredLoading] = useState(false);
  const [predError, setPredError] = useState<string | null>(null);

  const articles = useApi(() => api.getArticles({ limit: 3 }), []);
  const commentary = useApi(() => api.getCommentary(541), []);

  // Step 1: Try to fetch next fixture from API-Football
  useEffect(() => {
    setFixtureLoading(true);
    api.getNextFixture()
      .then((fixture) => {
        if (fixture && fixture.opponent) {
          setMatchInput({ opponent: fixture.opponent, venue: fixture.venue, date: fixture.date });
        } else {
          setUseManualForm(true);
        }
      })
      .catch(() => setUseManualForm(true))
      .finally(() => setFixtureLoading(false));
  }, []);

  // Step 2: Predict when matchInput is set
  useEffect(() => {
    if (!matchInput) return;
    setPredLoading(true);
    setPredError(null);
    api.predict(matchInput.opponent, matchInput.venue, matchInput.date)
      .then(setPrediction)
      .catch((e) => setPredError(e.message))
      .finally(() => setPredLoading(false));
  }, [matchInput]);

  const handleManualPredict = (e: React.FormEvent) => {
    e.preventDefault();
    setUseManualForm(false);
    setMatchInput({ opponent: manualOpponent, venue: manualVenue, date: manualDate });
  };

  const handleQuickChat = (e: React.FormEvent) => {
    e.preventDefault();
    if (quickChat.trim()) navigate(`/chat?prompt=${encodeURIComponent(quickChat)}`);
  };

  return (
    <div className="space-y-8 animate-fade-in-up">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Match Intelligence
        </h1>
        <p className="text-muted-foreground mt-1">Real-time predictions, news, and live insights</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Prediction */}
        {fixtureLoading || predLoading ? (
          <CardSkeleton />
        ) : useManualForm ? (
          <div className="glass-card p-6 space-y-4">
            <h3 className="text-lg font-semibold">Predict a Match</h3>
            <p className="text-sm text-muted-foreground">
              API-Football key not configured. Pick a match manually.
            </p>
            <form onSubmit={handleManualPredict} className="space-y-3">
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Opponent</label>
                <input
                  type="text"
                  value={manualOpponent}
                  onChange={(e) => setManualOpponent(e.target.value)}
                  placeholder="e.g. Barcelona"
                  className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Venue</label>
                  <select
                    value={manualVenue}
                    onChange={(e) => setManualVenue(e.target.value)}
                    className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="Home">Home</option>
                    <option value="Away">Away</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Date</label>
                  <input
                    type="date"
                    value={manualDate}
                    onChange={(e) => setManualDate(e.target.value)}
                    className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </div>
              <button
                type="submit"
                className="w-full bg-primary text-primary-foreground rounded-lg px-4 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors"
              >
                Predict
              </button>
            </form>
          </div>
        ) : predError ? (
          <ErrorBanner message="Could not load prediction" onRetry={() => window.location.reload()} />
        ) : prediction && matchInput ? (
          <div>
            <PredictionCard
              opponent={matchInput.opponent}
              venue={matchInput.venue}
              date={matchInput.date}
              win={prediction.win}
              draw={prediction.draw}
              loss={prediction.loss}
            />
            <button
              onClick={() => { setUseManualForm(true); setPrediction(null); }}
              className="mt-2 text-xs text-muted-foreground hover:text-primary transition-colors"
            >
              Change match →
            </button>
          </div>
        ) : null}

        {/* Live Match Status */}
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-primary" />
            <h3 className="text-lg font-semibold">Live Match Status</h3>
          </div>
          {commentary.loading ? (
            <CardSkeleton className="!p-0 !border-0 !shadow-none !bg-transparent !backdrop-blur-none" />
          ) : commentary.error ? (
            <div className="text-center py-6">
              <p className="text-muted-foreground text-sm">Backend unavailable</p>
            </div>
          ) : commentary.data?.message ? (
            <div className="text-center py-6 space-y-2">
              <p className="text-muted-foreground">{commentary.data.message}</p>
              <button
                onClick={() => navigate('/')}
                className="text-sm text-primary hover:underline"
              >
                View next match prediction →
              </button>
            </div>
          ) : commentary.data ? (
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
              {commentary.data.events && commentary.data.events.length > 0 && (
                <div className="mt-3 glass-card-static p-3 text-left">
                  <p className="text-xs text-muted-foreground mb-1">Latest event</p>
                  <p className="text-sm">
                    <span className="font-data text-primary">{commentary.data.events[commentary.data.events.length - 1].minute}'</span>{' '}
                    {commentary.data.events[commentary.data.events.length - 1].commentary}
                  </p>
                </div>
              )}
            </div>
          ) : null}
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

        {/* Quick Chat */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-lg font-semibold">Ask the Agent</h3>
          <form onSubmit={handleQuickChat} className="flex gap-2">
            <input
              type="text"
              value={quickChat}
              onChange={(e) => setQuickChat(e.target.value)}
              placeholder="Ask the agent anything..."
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
      </div>

      {/* Article reader modal */}
      {selectedArticle && (
        <ArticleReader
          article={selectedArticle}
          onClose={() => setSelectedArticle(null)}
        />
      )}
    </div>
  );
}
