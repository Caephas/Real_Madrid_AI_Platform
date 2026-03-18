import { cn } from '@/lib/utils';

const categoryColors: Record<string, string> = {
  'Breaking News': 'bg-destructive/20 text-destructive',
  'Transfers': 'bg-primary/20 text-primary',
  'Match Previews': 'bg-win/20 text-win',
  'Player Interviews': 'bg-secondary text-secondary-foreground',
  'Uncategorized': 'bg-muted text-muted-foreground',
};

interface CategoryBadgeProps {
  category: string;
  className?: string;
}

export function CategoryBadge({ category, className }: CategoryBadgeProps) {
  const color = categoryColors[category] || 'bg-muted text-muted-foreground';
  return (
    <span className={cn('badge-category', color, className)}>
      {category}
    </span>
  );
}
