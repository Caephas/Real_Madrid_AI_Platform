import { cn } from '@/lib/utils';

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorBanner({ message, onRetry, className }: ErrorBannerProps) {
  return (
    <div className={cn('glass-card-static border-destructive/30 p-4 flex items-center justify-between', className)}>
      <div className="flex items-center gap-3">
        <span className="text-destructive text-lg">⚠</span>
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs font-medium text-primary hover:underline"
        >
          Retry
        </button>
      )}
    </div>
  );
}
