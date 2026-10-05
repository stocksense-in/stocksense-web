import {
  ChartLine,
  Earth,
  FileSearch,
  LayoutDashboard,
  Rocket,
  SlidersHorizontal,
  Sparkles,
  UserRound,
  Wallet,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  pro?: boolean;
}

/** The app's sections, in sidebar order. Add a page here to put it in the navigation. */
export const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: 'Markets',
    items: [
      { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { href: '/stocks', label: 'Stocks', icon: ChartLine },
      { href: '/screener', label: 'Screener', icon: SlidersHorizontal },
    ],
  },
  {
    group: 'Research',
    items: [
      { href: '/ipo', label: 'IPOs', icon: Rocket },
      { href: '/rhp-analyser', label: 'Prospectus scanner', icon: FileSearch },
      { href: '/geopolitics', label: 'Geopolitics', icon: Earth },
    ],
  },
  {
    group: 'You',
    items: [
      { href: '/paper-trading', label: 'Paper trading', icon: Wallet },
      { href: '/profile', label: 'Investor profile', icon: UserRound },
      { href: '/premium', label: 'Matched picks', icon: Sparkles, pro: true },
    ],
  },
];
