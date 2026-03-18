import { useCallback, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, LiveMatchData } from '@/api/client';
import { usePolling } from '@/hooks/usePolling';
import { EventTimeline } from '@/components/EventTimeline';
import { CardSkeleton } from '@/components/LoadingSkeleton';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Radio } from 'lucide-react';

export default function LiveMatch() {
  const navigate = useNavigate();
  const fetcher = useCallback(() => api.getCommentary(541), []);
  const { data, loading, error, lastUpdated, refetch } = usePolling<LiveMatchData>(fetcher, 30000);
  const [secondsAgo, setSecondsAgo] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      if (lastUpdated) {
        setSecondsAgo(Math.floor((Date.now() - lastUpdated.getTime()) / 1000));
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [lastUpdated]);

  const isLive = data && !data.message;

  if (loading && !data) {
    return (
      <div className="space-y-6 animate-fade-in-up">
        <h1 className="text-3xl font-bold tracking-tight">Live Match</h1>
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Live Match</h1>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {isLive && (
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span className="live-pulse absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
              </span>
              <span className="text-primary font-medium">LIVE</span>
            </div>
          )}
          {lastUpdated && (
            <span>Updated {secondsAgo}s ago</span>
          )}
        </div>
      </div>

      {error && <ErrorBanner message="Could not connect to backend" onRetry={refetch} />}

      {data?.message ? (
        /* No live match */
        <div className="glass-card p-10 text-center space-y-4">
          <Radio className="w-12 h-12 mx-auto text-muted-foreground" />
          <h2 className="text-xl font-semibold">No Live Match Right Now</h2>
          <p className="text-muted-foreground">Check back when Real Madrid are playing</p>
          <button
            onClick={() => navigate('/')}
            className="bg-primary text-primary-foreground rounded-lg px-6 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors mt-2"
          >
            Predict Next Match →
          </button>
        </div>
      ) : data ? (
        <>
          {/* Match header */}
          <div className="glass-card-static p-6 text-center space-y-2">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">
              {data.match_status}
            </p>
            <p className="text-3xl font-bold font-data">
              {data.home_team} <span className="text-primary mx-3">{data.score}</span> {data.away_team}
            </p>
          </div>

          {/* Timeline */}
          <EventTimeline events={data.events || []} />
        </>
      ) : null}
    </div>
  );
}
