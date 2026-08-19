import { useCallback, useEffect, useRef, useState } from 'react';
import { api, CallJob } from '@/api/client';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { ErrorBanner } from '@/components/ErrorBanner';
import LoadingState from '@/components/ai/LoadingState';
import ThinkingState from '@/components/ai/ThinkingState';
import { Youtube, Upload, Send, RefreshCcw, ShieldQuestion } from 'lucide-react';
import { cn } from '@/lib/utils';

const STATUS_LABELS: Record<string, string> = {
  queued: 'Queued',
  extracting: 'Extracting frames',
  analyzing: 'Reviewing the call',
};

const VERDICT_META: Record<string, { label: string; color: string; bg: string }> = {
  correct_call: { label: 'Correct call', color: '#2ebd85', bg: 'rgba(46,189,133,0.12)' },
  incorrect_call: { label: 'Wrong call', color: '#ef5350', bg: 'rgba(239,83,80,0.12)' },
  unclear: { label: 'Inconclusive', color: '#f2b900', bg: 'rgba(242,185,0,0.12)' },
};

function nearestCaption(timestamp: number, keyFrames: { timestamp: number; caption: string }[]) {
  if (!keyFrames.length) return null;
  return keyFrames.reduce((best, kf) =>
    Math.abs(kf.timestamp - timestamp) < Math.abs(best.timestamp - timestamp) ? kf : best
  ).caption;
}

export default function Calls() {
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [note, setNote] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [competition, setCompetition] = useState('La Liga');
  const [decisionType, setDecisionType] = useState('auto');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [job, setJob] = useState<CallJob | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const submit = useCallback(async () => {
    if (!youtubeUrl.trim() && !file) return;
    setSubmitting(true);
    setSubmitError(null);
    setJob(null);
    try {
      const created = await api.analyzeCall(
        youtubeUrl.trim() || undefined,
        note.trim() || undefined,
        file ?? undefined,
        competition,
        decisionType
      );
      setJobId(created.job_id);
      setJob(created);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : 'Could not start analysis');
    } finally {
      setSubmitting(false);
    }
  }, [youtubeUrl, note, file, competition, decisionType]);

  // Poll while the job is active
  useEffect(() => {
    if (!jobId || (job && (job.status === 'done' || job.status === 'error'))) return;
    let stop = false;
    const poll = async () => {
      try {
        const latest = await api.getCall(jobId);
        if (!stop) setJob(latest);
      } catch {
        // transient — keep polling
      }
    };
    poll();
    const timer = setInterval(poll, 2500);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, [jobId, job?.status]);

  const reset = () => {
    setJob(null);
    setJobId(null);
    setYoutubeUrl('');
    setNote('');
    setFile(null);
    if (fileRef.current) fileRef.current.value = '';
  };

  const active = job && (job.status === 'queued' || job.status === 'extracting' || job.status === 'analyzing');
  const result = job?.result;
  const verdict = result ? VERDICT_META[result.verdict] ?? VERDICT_META.unclear : null;

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <ShieldQuestion className="w-7 h-7 text-primary" />
          Call Review
        </h1>
        <p className="text-muted-foreground mt-1">
          Paste a YouTube link or upload a clip — the AI watches it frame by frame and judges the referee's decision.
        </p>
      </div>

      {!job && (
        <div className="glass-card p-6 space-y-4">
          <div className="grid grid-cols-1 gap-3">
            <div className="flex items-center gap-2 bg-muted/20 rounded-lg px-3 py-2.5 border border-border/50">
              <Youtube className="w-4 h-4 text-primary flex-shrink-0" />
              <input
                type="url"
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                placeholder="https://youtube.com/... (the incident clip)"
                className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
              />
            </div>
            <div className="flex items-center gap-2 bg-muted/20 rounded-lg px-3 py-2.5 border border-border/50">
              <Upload className="w-4 h-4 text-primary flex-shrink-0" />
              <input
                ref={fileRef}
                type="file"
                accept="video/*"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="flex-1 text-sm text-muted-foreground file:mr-3 file:rounded-md file:border-0 file:bg-primary/15 file:px-3 file:py-1 file:text-primary file:text-xs"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="block">
                <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Competition</span>
                <select
                  value={competition}
                  onChange={(e) => setCompetition(e.target.value)}
                  className="mt-1 w-full bg-muted/20 border border-border/50 rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option>La Liga</option>
                  <option>UEFA Champions League</option>
                  <option>Other</option>
                </select>
              </label>
              <label className="block">
                <span className="text-[11px] uppercase tracking-wider text-muted-foreground">What kind of call?</span>
                <select
                  value={decisionType}
                  onChange={(e) => setDecisionType(e.target.value)}
                  className="mt-1 w-full bg-muted/20 border border-border/50 rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="auto">Auto-detect</option>
                  <option value="penalty">Penalty</option>
                  <option value="foul">Foul</option>
                  <option value="offside">Offside</option>
                  <option value="handball">Handball</option>
                  <option value="red_card">Red card</option>
                  <option value="yellow_card">Yellow card</option>
                  <option value="clean">Clean / no offence</option>
                </select>
              </label>
            </div>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Optional: what happened? e.g. 'Penalty shout in the box, 2nd half'"
              rows={2}
              className="bg-muted/20 border border-border/50 rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
            />
          </div>

          {submitError && <ErrorBanner message={submitError} onRetry={submit} />}

          <button
            onClick={submit}
            disabled={submitting || (!youtubeUrl.trim() && !file)}
            className="bg-primary text-primary-foreground rounded-lg px-5 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-40 flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            {submitting ? 'Starting…' : 'Analyze the call'}
          </button>
          {!youtubeUrl.trim() && !file && (
            <p className="text-xs text-muted-foreground">Add a YouTube link or a video file to continue.</p>
          )}
        </div>
      )}

      {active && (
        <div className="glass-card p-6 space-y-5">
          <LoadingState label={STATUS_LABELS[job.status] ?? 'Working'} variant={job.status === 'extracting' ? 'Drive' : 'Orbit'} />
          <ThinkingState
            variant="Coding"
            activeLabel={STATUS_LABELS[job.status] ?? 'Working'}
            doneLabel="Analysis complete"
            rows={[
              { primary: 'Video', secondary: jobId ?? '', mono: true },
              ...(job.status === 'extracting'
                ? [{ primary: 'Frames', secondary: 'sampling…', mono: true }]
                : [
                    { primary: 'Frames', secondary: 'extracted', mono: true },
                    { primary: 'Vision model', secondary: 'judging the call', mono: true },
                  ]),
            ]}
          />
        </div>
      )}

      {job?.status === 'error' && (
        <div className="space-y-4">
          <ErrorBanner message={job.error ?? 'Analysis failed'} onRetry={submit} />
          <button onClick={reset} className="text-sm text-primary hover:underline">Analyze another clip →</button>
        </div>
      )}

      {job?.status === 'done' && result && verdict && (
        <div className="space-y-6">
          {/* Verdict banner */}
          <div className="glass-card p-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Verdict</p>
                <h2 className="text-2xl font-bold" style={{ color: verdict.color }}>{verdict.label}</h2>
                <span
                  className="inline-flex items-center gap-1.5 mt-2 rounded-full px-3 py-1 text-xs font-medium"
                  style={{ color: verdict.color, background: verdict.bg }}
                >
                  {result.decision_type.replace(/_/g, ' ')}
                </span>
              </div>
              <div className="text-right">
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Confidence</p>
                <p className="text-3xl font-bold font-data text-primary">{result.confidence}%</p>
                <div className="w-40 h-1.5 rounded-full bg-muted/30 mt-2 overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${result.confidence}%`, background: verdict.color }}
                  />
                </div>
              </div>
            </div>
            <p className="mt-4 text-sm text-foreground/85 leading-relaxed">{result.summary}</p>
            {result.laws_cited && result.laws_cited.length > 0 && (
              <div className="mt-4 flex flex-wrap items-center gap-1.5">
                <span className="text-[11px] uppercase tracking-wider text-muted-foreground mr-1">
                  Laws applied
                </span>
                {result.laws_cited.map((law) => (
                  <span
                    key={law}
                    className="text-[11px] font-mono font-medium text-primary bg-primary/10 border border-primary/20 rounded-full px-2.5 py-1"
                  >
                    {law}
                  </span>
                ))}
                {result.competition && (
                  <span className="text-[11px] text-muted-foreground ml-2">
                    · {result.competition}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Reasoning */}
          <div className="glass-card p-6 space-y-4">
            <h3 className="text-lg font-semibold">Why the AI thinks so</h3>
            {result.reasoning.length ? (
              <div className="space-y-3">
                {result.reasoning.map((step, i) => (
                  <div key={i} className="flex gap-3">
                    <span className="font-data text-xs text-primary font-bold pt-0.5 w-14 shrink-0">
                      {step.timestamp}s
                    </span>
                    <div className="border-l border-border/50 pl-4 space-y-0.5">
                      <p className="text-sm text-foreground/90">{step.observation}</p>
                      <p className="text-xs text-muted-foreground">{step.assessment}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <LoadingSkeleton lines={3} />
            )}
          </div>

          {/* Key frames */}
          {result.frames && result.frames.length > 0 && (
            <div className="glass-card p-6 space-y-4">
              <h3 className="text-lg font-semibold">Frames reviewed ({result.frames.length})</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {result.frames.map((frame) => (
                  <div key={frame.file} className="rounded-lg overflow-hidden border border-border/40 bg-muted/10">
                    <img
                      src={api.callFrameUrl(job.job_id, frame.file)}
                      alt={`Frame at ${frame.timestamp}s`}
                      loading="lazy"
                      className="w-full aspect-video object-cover"
                    />
                    <div className="p-2 space-y-0.5">
                      <p className="text-[10px] font-data text-primary font-bold">{frame.timestamp}s</p>
                      <p className="text-[11px] text-muted-foreground leading-snug">
                        {nearestCaption(frame.timestamp, result.key_frames) ?? 'Frame'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={reset}
            className="flex items-center gap-2 text-sm text-primary hover:underline"
          >
            <RefreshCcw className="w-3.5 h-3.5" />
            Analyze another clip
          </button>
        </div>
      )}
    </div>
  );
}
