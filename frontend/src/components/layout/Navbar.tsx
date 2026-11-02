'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { ThemeToggle, useTheme, Button } from '@/kit';

export function Navbar() {
  const { user, logout } = useAuth();
  const { dark, toggle } = useTheme();

  return (
    <header className="border-b border-border/80 bg-background/95 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand / Logo */}
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-3">
            <img
              src="/icon.png"
              alt="MnemoGraph Logo"
              className="w-9 h-9 rounded object-contain drop-shadow-[0_0_10px_rgba(14,165,233,0.35)]"
            />
            <div className="flex items-center gap-2">
              <span className="font-semibold text-lg tracking-tight text-foreground">
                MnemoGraph
              </span>
              <span className="font-mono text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted border border-border text-muted-foreground font-medium">
                CORE
              </span>
            </div>
          </Link>

          {user && (
            <nav className="hidden md:flex items-center gap-5 text-sm font-medium">
              <Link
                href="/search"
                className="text-accent font-semibold hover:text-foreground transition-colors"
              >
                Search & Q&A
              </Link>
              <Link
                href="/connectors"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                Connectors
              </Link>
              <Link
                href="/hub"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                Knowledge Hub
              </Link>
            </nav>
          )}
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          <ThemeToggle dark={dark} onToggle={toggle} />

          {user ? (
            <div className="flex items-center gap-3">
              <Link href="/profile">
                <div className="flex items-center gap-2 p-1 pl-2 pr-3 rounded border border-border bg-card/60 hover:border-accent/40 transition-colors cursor-pointer">
                  <img
                    src={user.image_url}
                    alt={user.full_name}
                    className="w-6 h-6 rounded-full object-cover border border-border"
                  />
                  <span className="text-xs font-mono font-medium truncate max-w-[120px]">
                    {user.full_name}
                  </span>
                </div>
              </Link>
              <Button variant="ghost" onClick={logout} className="text-xs h-8 px-3">
                Sign Out
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link href="/login">
                <Button variant="ghost" className="text-xs h-8 px-3">
                  Sign In
                </Button>
              </Link>
              <Link href="/register">
                <Button className="text-xs h-8 px-3.5 bg-accent text-accent-foreground font-semibold shadow-[0_0_15px_rgba(14,165,233,0.35)]">
                  Setup Company
                </Button>
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

