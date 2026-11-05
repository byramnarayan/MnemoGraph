'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { Button, Eyebrow, Field, Callout } from '@/kit';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isSessionExpired, setIsSessionExpired] = useState(false);

  React.useEffect(() => {
    if (typeof window !== 'undefined' && window.location.search.includes('expired=true')) {
      setIsSessionExpired(true);
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login({ email, password });
      router.push('/profile');
    } catch (err: any) {
      setError(err.message || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-md mx-auto">
      <div className="border border-border/80 bg-card/60 backdrop-blur-sm rounded-lg p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        {/* Glow ambient background effect */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-accent/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        <div className="space-y-2 mb-6">
          <Eyebrow>AUTHENTICATION · ENTERPRISE RBAC</Eyebrow>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Sign in to MnemoGraph
          </h1>
          <p className="text-xs text-muted-foreground">
            Enter your official enterprise credentials to access your tenant knowledge graph.
          </p>
        </div>

        {isSessionExpired && !error && (
          <div className="mb-6">
            <Callout tone="warn" title="Session Expired">
              Your security session has expired. Please sign in to reconnect.
            </Callout>
          </div>
        )}

        {error && (
          <div className="mb-6">
            <Callout tone="bad" title="Access Denied">
              {error}
            </Callout>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <Field
            label="OFFICIAL WORK EMAIL *"
            type="email"
            placeholder="admin@enterprise.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <Field
            label="MASTER PASSWORD *"
            type="password"
            placeholder="••••••••••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <div className="flex items-center justify-between text-xs pt-1">
            <label className="flex items-center gap-2 cursor-pointer text-muted-foreground hover:text-foreground">
              <input type="checkbox" className="rounded border-border accent-accent" />
              <span>Remember session</span>
            </label>
            <Link href="#" className="text-muted-foreground hover:text-accent font-mono transition-colors">
              Forgot password?
            </Link>
          </div>

          <div className="pt-4">
            <Button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-accent text-accent-foreground font-semibold rounded shadow-[0_0_20px_rgba(14,165,233,0.35)] hover:shadow-[0_0_25px_rgba(14,165,233,0.5)] transition-all flex items-center justify-center gap-2"
            >
              {loading ? 'Authenticating...' : 'Sign In to Brain →'}
            </Button>
          </div>
        </form>

        <div className="mt-6 pt-6 border-t border-border/60 text-center">
          <p className="text-xs text-muted-foreground">
            Don't have an enterprise tenant yet?{' '}
            <Link href="/register" className="text-accent font-semibold hover:underline">
              Provision Company Brain
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

