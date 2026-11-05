import { useEffect, useState } from 'react'
import type { InputHTMLAttributes, ReactNode } from 'react'

export function Frame({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`mx-auto w-full max-w-[1300px] border-x border-border px-5 lg:px-12 ${className}`}>
      {children}
    </div>
  )
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div className="font-mono text-[12px] font-medium uppercase tracking-[0.14em] text-accent">{children}</div>
  )
}

export function Section({
  n,
  label,
  title,
  lede,
  action,
  children,
  delay = 0,
}: {
  n: string
  label: string
  title: ReactNode
  lede?: ReactNode
  action?: ReactNode
  children?: ReactNode
  delay?: number
}) {
  return (
    <section className="dashed-b">
      <Frame className="py-12 lg:py-14">
        <div
          className="rise flex flex-col items-start justify-between gap-6 lg:flex-row lg:items-end"
          style={{ animationDelay: `${delay}ms` }}
        >
          <div className="max-w-2xl">
            <Eyebrow>
              {n} / {label}
            </Eyebrow>
            <h2 className="mt-5 text-3xl font-medium tracking-tight md:text-5xl md:leading-[1.05]">{title}</h2>
            {lede && <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-muted-foreground">{lede}</p>}
          </div>
          {action}
        </div>
        {children && (
          <div className="rise mt-10" style={{ animationDelay: `${delay + 100}ms` }}>
            {children}
          </div>
        )}
      </Frame>
    </section>
  )
}

type Tone = 'neutral' | 'accent' | 'ok' | 'warn' | 'bad' | 'info'
const tones: Record<Tone, string> = {
  neutral: 'border-border text-muted-foreground',
  accent: 'border-accent/40 bg-accent-soft text-accent',
  ok: 'border-ok/40 bg-ok/10 text-ok',
  warn: 'border-warn/40 bg-warn/10 text-warn',
  bad: 'border-bad/40 bg-bad/10 text-bad',
  info: 'border-info/40 bg-info/10 text-info',
}

export function Tag({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-xs border px-1.5 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider ${tones[tone]}`}
    >
      {children}
    </span>
  )
}

export function Panel({
  title,
  meta,
  children,
  className = '',
}: {
  title?: ReactNode
  meta?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`rounded-sm border border-border bg-card ${className}`}>
      {title && (
        <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-2.5">
          <div className="font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">{title}</div>
          {meta}
        </div>
      )}
      {children}
    </div>
  )
}

export function Button({
  children,
  onClick,
  variant = 'primary',
  disabled,
  type = 'button',
  className = '',
}: {
  children: ReactNode
  onClick?: () => void
  variant?: 'primary' | 'ghost'
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
  className?: string
}) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-sm px-4 py-2 text-sm font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-40'
  const v =
    variant === 'primary'
      ? 'bg-accent text-accent-foreground hover:opacity-90'
      : 'border border-border text-foreground hover:bg-muted'
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={`${base} ${v} ${className}`}>
      {children}
    </button>
  )
}

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: readonly T[]
  value: T
  onChange: (v: T) => void
  label: string
}) {
  return (
    <div role="tablist" aria-label={label} className="inline-flex flex-wrap items-center gap-1 rounded-sm border border-border bg-background p-1">
      {options.map((o) => (
        <button
          key={o}
          role="tab"
          aria-selected={o === value}
          onClick={() => onChange(o)}
          className={`rounded-xs px-3 py-1.5 font-mono text-xs transition-colors duration-200 ${
            o === value ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          {o}
        </button>
      ))}
    </div>
  )
}

export function Meter({ value, tone = 'accent' }: { value: number; tone?: 'accent' | 'ok' | 'warn' | 'bad' }) {
  const c = { accent: 'bg-accent', ok: 'bg-ok', warn: 'bg-warn', bad: 'bg-bad' }[tone]
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
      <div className={`h-full ${c} transition-all duration-700`} style={{ width: `${Math.round(value * 100)}%` }} />
    </div>
  )
}

export function scoreTone(v: number): 'ok' | 'warn' | 'bad' {
  return v >= 0.8 ? 'ok' : v >= 0.6 ? 'warn' : 'bad'
}

export function Stat({ k, v, sub }: { k: string; v: ReactNode; sub?: string }) {
  return (
    <div className="p-5">
      <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted-foreground">{k}</div>
      <div className="mt-3 text-4xl font-medium tracking-tight tabular-nums md:text-5xl">{v}</div>
      {sub && <div className="mt-2 text-xs text-muted-foreground">{sub}</div>}
    </div>
  )
}

export function StatRow({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-2 divide-border overflow-hidden rounded-sm border border-border bg-card md:grid-cols-4 [&>*]:border-border max-md:[&>*:nth-child(n+3)]:border-t max-md:[&>*:nth-child(even)]:border-l md:[&>*+*]:border-l">
      {children}
    </div>
  )
}

/* ---------- Form ---------- */

export function Field({
  label,
  hint,
  ...props
}: { label: string; hint?: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">{label}</span>
      <input
        {...props}
        className="mt-1.5 w-full rounded-sm border border-border bg-background px-3 py-2 font-mono text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-accent"
      />
      {hint && <span className="mt-1 block text-xs text-muted-foreground">{hint}</span>}
    </label>
  )
}

/* ---------- Data display ---------- */

export function DataTable<R>({
  columns,
  rows,
  rowKey,
  minWidth = 640,
}: {
  columns: { key: string; header: string; render: (row: R) => ReactNode; className?: string }[]
  rows: R[]
  rowKey: (row: R) => string
  minWidth?: number
}) {
  return (
    <div className="overflow-x-auto rounded-sm border border-border bg-card">
      <table className="w-full text-left text-sm" style={{ minWidth }}>
        <thead>
          <tr className="border-b border-border font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {columns.map((c) => (
              <th key={c.key} className="px-4 py-3 font-medium">
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={rowKey(r)} className="border-b border-border transition-colors last:border-0 hover:bg-muted">
              {columns.map((c) => (
                <td key={c.key} className={`px-4 py-3 ${c.className ?? ''}`}>
                  {c.render(r)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Stepper({
  steps,
  current,
  onSelect,
}: {
  steps: { title: string; detail?: string }[]
  current: number
  onSelect?: (i: number) => void
}) {
  return (
    <ol>
      {steps.map((s, i) => (
        <li key={s.title} className={i > 0 ? 'border-t border-border' : ''}>
          <button
            type="button"
            onClick={() => onSelect?.(i)}
            className={`flex w-full items-start gap-4 px-4 py-4 text-left transition-colors ${
              i === current ? 'bg-accent-soft' : 'hover:bg-muted'
            }`}
          >
            <span
              className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-full border font-mono text-[11px] ${
                i < current
                  ? 'border-ok bg-ok/15 text-ok'
                  : i === current
                    ? 'border-accent bg-accent text-accent-foreground'
                    : 'border-border text-muted-foreground'
              }`}
            >
              {i < current ? '✓' : i + 1}
            </span>
            <span>
              <span className="block font-medium">{s.title}</span>
              {s.detail && <span className="mt-1 block text-sm text-muted-foreground">{s.detail}</span>}
            </span>
          </button>
        </li>
      ))}
    </ol>
  )
}

export function Callout({ tone = 'accent', title, children }: { tone?: Tone; title?: string; children: ReactNode }) {
  return (
    <div className={`rounded-sm border px-4 py-3 text-sm ${tones[tone]}`}>
      {title && <div className="mb-1 font-mono text-[11px] font-semibold uppercase tracking-wider">{title}</div>}
      <div className="text-foreground/90">{children}</div>
    </div>
  )
}

export function CodeBlock({ children, title }: { children: string; title?: string }) {
  return (
    <Panel title={title}>
      <pre className="overflow-x-auto p-4 font-mono text-[12.5px] leading-6 text-foreground/85">{children}</pre>
    </Panel>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="hatch grid min-h-[240px] place-items-center p-8 text-center">
      <div className="max-w-xs rounded-sm border border-border bg-card p-5">
        <div className="font-mono text-xs uppercase text-accent">{title}</div>
        {children && <p className="mt-2 text-sm text-muted-foreground">{children}</p>}
      </div>
    </div>
  )
}

/* ---------- Chrome ---------- */

export function useTheme(initial: 'dark' | 'light' = 'dark') {
  const [dark, setDark] = useState<boolean>(initial === 'dark');
  const [mounted, setMounted] = useState<boolean>(false);

  useEffect(() => {
    setMounted(true);
    const stored = localStorage.getItem('mnemograph_theme');
    if (stored) {
      setDark(stored === 'dark');
    } else {
      setDark(document.documentElement.classList.contains('dark') || initial === 'dark');
    }
  }, [initial]);

  useEffect(() => {
    if (mounted) {
      document.documentElement.classList.toggle('dark', dark);
      localStorage.setItem('mnemograph_theme', dark ? 'dark' : 'light');
    }
  }, [dark, mounted]);

  return { dark, toggle: () => setDark((d) => !d), mounted };
}

export function ThemeToggle({ dark, onToggle }: { dark: boolean; onToggle: () => void }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={mounted ? dark : true}
      aria-label="Toggle theme"
      className="rounded-sm border border-border px-2.5 py-1.5 font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
    >
      {mounted ? (dark ? 'DARK' : 'LIGHT') : 'DARK'}
    </button>
  )
}

export function Header({ logo, nav, actions }: { logo: ReactNode; nav?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur">
      <Frame className="flex h-14 items-center justify-between gap-4">
        {logo}
        {nav}
        <div className="flex items-center gap-2">{actions}</div>
      </Frame>
    </header>
  )
}

export function StickyBanner({ children, action, onDismiss }: { children: ReactNode; action?: ReactNode; onDismiss?: () => void }) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-background/95 backdrop-blur">
      <Frame className="flex items-center justify-between gap-4 py-3">
        <div className="min-w-0 truncate text-sm">{children}</div>
        <div className="flex shrink-0 items-center gap-2">
          {action}
          {onDismiss && (
            <button type="button" onClick={onDismiss} aria-label="Dismiss" className="px-2 text-muted-foreground hover:text-foreground">
              ✕
            </button>
          )}
        </div>
      </Frame>
    </div>
  )
}
