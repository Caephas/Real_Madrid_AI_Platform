import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, MessageCircle, Radio, Newspaper, CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react';
import madridCrest from '@/assets/madrid-crest.png';
import { cn } from '@/lib/utils';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/fixtures', label: 'Fixtures', icon: CalendarDays },
  { path: '/chat', label: 'Chat', icon: MessageCircle },
  { path: '/live', label: 'Live Match', icon: Radio },
  { path: '/news', label: 'News', icon: Newspaper },
];

export function AppSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <>
      {/* Mobile overlay */}
      <aside
        className={cn(
          'fixed top-0 left-0 h-full z-50 flex flex-col transition-all duration-300',
          'bg-sidebar border-r border-sidebar-border',
          collapsed ? 'w-[72px]' : 'w-[260px]'
        )}
      >
        {/* Brand */}
        <div className={cn(
          'flex items-center gap-3 p-5 border-b border-sidebar-border',
          collapsed && 'justify-center px-3'
        )}>
          <img src={madridCrest} alt="Real Madrid" className="w-9 h-9 object-contain flex-shrink-0" />
          {!collapsed && (
            <div className="overflow-hidden">
              <h1 className="text-sm font-bold text-foreground tracking-tight leading-tight">Real Madrid</h1>
              <p className="text-xs text-primary font-data">AI PLATFORM</p>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => {
            const active = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  active
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-sidebar-accent',
                  collapsed && 'justify-center px-2'
                )}
                title={collapsed ? item.label : undefined}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-3 border-t border-sidebar-border text-muted-foreground hover:text-foreground transition-colors flex items-center justify-center"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </aside>

      {/* Spacer */}
      <div className={cn('flex-shrink-0 transition-all duration-300', collapsed ? 'w-[72px]' : 'w-[260px]')} />
    </>
  );
}
