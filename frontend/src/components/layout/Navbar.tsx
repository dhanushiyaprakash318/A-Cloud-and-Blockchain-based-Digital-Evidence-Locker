import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Home, GitBranch, Map, MessageSquare, Shield, ScanFace } from 'lucide-react';
import { cn } from '@/lib/utils';
import ThemeToggle from '@/components/ThemeToggle';
// GooeyNav removed per user request
import { useRole, UserRole } from '@/contexts/RoleContext';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const navItems = [
  { path: '/', label: 'Deepfake Detector', icon: ScanFace },
  { path: '/dashboard', label: 'Dashboard', icon: Home },
  { path: '/knowledge-graph', label: 'Knowledge Graph', icon: GitBranch },
  { path: '/heatmap', label: 'Heatmap', icon: Map },
  { path: '/chatbot', label: 'Chatbot', icon: MessageSquare },
];

const roleLabels: Record<UserRole, string> = {
  police: 'Police',
  judge: 'Judge',
  forensics: 'Forensics',
};

const roleColors: Record<UserRole, string> = {
  police: 'bg-primary text-primary-foreground',
  judge: 'bg-warning text-warning-foreground',
  forensics: 'bg-success text-success-foreground',
};

export const Navbar: React.FC = () => {
  const location = useLocation();
  const { role, setRole } = useRole();
  const activeIdx = Math.max(0, navItems.findIndex(i => i.path === location.pathname));

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
      <div className="container flex h-16 items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
            <Shield className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="font-display text-xl font-bold text-foreground">
            Divel
          </span>
        </Link>

        {/* Centered Navigation */}
        <div className="hidden md:flex items-center">
          <nav className="flex items-center gap-6">
            {navItems.map((n, idx) => (
              <Link
                key={n.path}
                to={n.path}
                className={cn('text-sm font-medium transition-colors', idx === activeIdx ? 'text-primary' : 'text-muted-foreground')}
              >
                {n.label}
              </Link>
            ))}
          </nav>
        </div>

        {/* Role Switcher */}
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <span className="text-xs text-muted-foreground hidden sm:block">Role:</span>
          <Select value={role} onValueChange={(value: UserRole) => setRole(value)}>
            <SelectTrigger className={cn('w-[130px] h-9', roleColors[role])}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="police">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-primary" />
                  Police
                </div>
              </SelectItem>
              <SelectItem value="judge">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-warning" />
                  Judge
                </div>
              </SelectItem>
              <SelectItem value="forensics">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-success" />
                  Forensics
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </header>
  );
};