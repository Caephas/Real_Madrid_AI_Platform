import { StandingRow } from '@/api/client';
import { cn } from '@/lib/utils';

const FORM_COLORS: Record<string, string> = {
  W: 'bg-win/20 text-win',
  D: 'bg-draw/20 text-draw',
  L: 'bg-loss/20 text-loss',
};

export function StandingsTable({ standings }: { standings: StandingRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[11px] text-muted-foreground uppercase tracking-wider">
            <th className="py-2 pr-2 font-medium">#</th>
            <th className="py-2 pr-3 font-medium">Team</th>
            <th className="py-2 px-2 font-medium text-center">P</th>
            <th className="py-2 px-2 font-medium text-center">W</th>
            <th className="py-2 px-2 font-medium text-center">D</th>
            <th className="py-2 px-2 font-medium text-center">L</th>
            <th className="py-2 px-2 font-medium text-center hidden sm:table-cell">GD</th>
            <th className="py-2 px-2 font-medium text-center">Pts</th>
            <th className="py-2 pl-3 font-medium text-right hidden md:table-cell">Form</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((row) => {
            const isRM = row.team === 'Real Madrid';
            return (
              <tr
                key={row.team}
                className={cn(
                  'border-t border-border/40',
                  isRM && 'bg-primary/10'
                )}
              >
                <td className={cn('py-2 pr-2 font-data', isRM && 'text-primary font-bold')}>
                  {row.position}
                </td>
                <td className={cn('py-2 pr-3 font-medium', isRM && 'text-primary')}>
                  {row.team}
                </td>
                <td className="py-2 px-2 text-center font-data text-muted-foreground">{row.played}</td>
                <td className="py-2 px-2 text-center font-data">{row.won}</td>
                <td className="py-2 px-2 text-center font-data">{row.drawn}</td>
                <td className="py-2 px-2 text-center font-data">{row.lost}</td>
                <td className="py-2 px-2 text-center font-data text-muted-foreground hidden sm:table-cell">
                  {row.gd > 0 ? `+${row.gd}` : row.gd}
                </td>
                <td className="py-2 px-2 text-center font-data font-bold">{row.points}</td>
                <td className="py-2 pl-3 hidden md:flex justify-end gap-1">
                  {row.form.map((f, i) => (
                    <span
                      key={i}
                      className={cn(
                        'w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold font-data',
                        FORM_COLORS[f] ?? 'bg-muted text-muted-foreground'
                      )}
                    >
                      {f}
                    </span>
                  ))}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
