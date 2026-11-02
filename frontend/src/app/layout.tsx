import type { Metadata } from 'next';
import { Inter, Geist_Mono } from 'next/font/google';
import '@/index.css';
import { AuthProvider } from '@/lib/auth-context';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
});

const geistMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
});

export const metadata: Metadata = {
  title: 'MnemoGraph Enterprise Intelligence',
  description: 'Enterprise Multi-Tenant Collective Memory & Institutional Knowledge Graph',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.variable} ${geistMono.variable} font-sans bg-background text-foreground antialiased min-h-screen flex flex-col`} suppressHydrationWarning>
        <AuthProvider>
          <Navbar />
          <main className="flex-1">
            {children}
          </main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}

