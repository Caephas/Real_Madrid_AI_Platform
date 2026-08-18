// File: frontend/src/components/MatchAnalysis.tsx
import { useState, useEffect } from 'react';
import { api, MatchAnalysis as MatchAnalysisData } from '@/api/client';
import { Brain, TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp } from 'lucide-react';
import LoadingState from '@/components/ai/LoadingState';

interface Props {
  opponent: string;
  venue: string;
  date: string;
}

function StatRow({ label, rm, opp }: { label: string; rm: number; opp: number }) {
  const rmWins = rm > opp;
  const oppWins = opp > rm;
  const isDefense = label === 'Goals Conceded';
  // For defense, lower is better
  const rmBetter = isDefense ? rm < opp : rm > opp;

  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 py-1.5">
      <span className={`text-right font-data text-sm ${rmBetter ? 'text-primary font-semibold' : 'text-foreground'}`}>
        {rm.toFixed(1)}
      </span>
      <span className="text-xs text-muted-foreground text-center w-28">{label}</span>
      <span className={`text-left font-data text-sm ${!rmBetter && rm !== opp ? 'text-primary font-semibold' : 'text-foreground'}`}>
        {opp.toFixed(1)}
      </span>
    </div>
  );
}

export function MatchAnalysis({ opponent, venue, date }: Props) {
  const [analysis, setAnalysis] = useState<MatchAnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setAnalysis(null);
    setExpanded(false);
    api.predictWithAnalysis(opponent, venue, date)
      .then(setAnalysis)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [opponent, venue, date]);

  if (loading) {
    return (
      <div className="glass-card p-8">
        <div className="flex items-start gap-3">
          <Brain className="w-4 h-4 text-primary mt-0.5" />
          <LoadingState label="Generating tactical analysis" variant="Dots" />
        </div>
      </div>
    );
  }

  if (error || !analysis) return null;

  const rm = analysis.real_madrid_form;
  const opp = analysis.opponent_form;

  return (
    <div className="glass-card overflow-hidden">
      {/* Key Factors — always visible */}
      <div className="p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-primary" />
          <h3 className="text-lg font-semibold">Match Analysis</h3>
        </div>

        {/* Key Factors */}
        <div className="space-y-2">
          {analysis.key_factors.map((factor, i) => (
            <div key={i} className="flex items-start gap-2 text-sm">
              <span className="text-primary mt-0.5">
                {factor.toLowerCase().includes('advantage') || factor.toLowerCase().includes('outscoring') || factor.toLowerCase().includes('more clinical') || factor.toLowerCase().includes('more chances')
                  ? <TrendingUp className="w-3.5 h-3.5" />
                  : factor.toLowerCase().includes('harder') || factor.toLowerCase().includes('tighter defense')
                    ? <TrendingDown className="w-3.5 h-3.5" />
                    : <Minus className="w-3.5 h-3.5" />}
              </span>
              <span className="text-foreground/90">{factor}</span>
            </div>
          ))}
        </div>

        {/* Form Comparison Table */}
        <div className="mt-4">
          <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 pb-2 border-b border-border/50">
            <span className="text-right text-xs font-semibold text-primary uppercase tracking-wide">Real Madrid</span>
            <span className="text-xs text-muted-foreground text-center w-28">Last 5 Games</span>
            <span className="text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">{opponent}</span>
          </div>
          <StatRow label="Goals Scored" rm={rm.goals_scored} opp={opp.goals_scored} />
          <StatRow label="Goals Conceded" rm={rm.goals_conceded} opp={opp.goals_conceded} />
          <StatRow label="Shots" rm={rm.shots} opp={opp.shots} />
          <StatRow label="Shots on Target" rm={rm.shots_on_target} opp={opp.shots_on_target} />
          <StatRow label="Shot Distance" rm={rm.shot_distance} opp={opp.shot_distance} />
        </div>
      </div>

      {/* Expandable AI Narrative */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-6 py-3 bg-muted/10 hover:bg-muted/20 transition-colors border-t border-border/30"
      >
        <span className="text-sm font-medium text-muted-foreground">AI Tactical Breakdown</span>
        {expanded ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
      </button>
      {expanded && (
        <div className="px-6 pb-6 pt-3">
          <p className="text-sm text-foreground/85 leading-relaxed whitespace-pre-line">
            {analysis.ai_narrative}
          </p>
        </div>
      )}
    </div>
  );
}
