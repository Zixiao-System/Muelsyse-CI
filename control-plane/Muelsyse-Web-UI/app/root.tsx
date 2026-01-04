import {
  isRouteErrorResponse,
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";
import LiquidGlass from "liquid-glass-react";

import type { Route } from "./+types/root";
import "./app.css";

export const links: Route.LinksFunction = () => [
  { rel: "preconnect", href: "https://fonts.googleapis.com" },
  {
    rel: "preconnect",
    href: "https://fonts.gstatic.com",
    crossOrigin: "anonymous",
  },
  {
    rel: "stylesheet",
    href: "https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap",
  },
];

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="antialiased">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#1e40af" />
        <Meta />
        <Links />
      </head>
      <body className="min-h-screen">
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function App() {
  return <Outlet />;
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  let message = "Oops!";
  let details = "An unexpected error occurred.";
  let stack: string | undefined;

  if (isRouteErrorResponse(error)) {
    message = error.status === 404 ? "404" : "Error";
    details =
      error.status === 404
        ? "The requested page could not be found."
        : error.statusText || details;
  } else if (import.meta.env.DEV && error && error instanceof Error) {
    details = error.message;
    stack = error.stack;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 via-blue-50 to-purple-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 flex items-center justify-center p-4">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-red-300 dark:bg-red-900 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-30 animate-blob" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-orange-300 dark:bg-orange-900 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-30 animate-blob animation-delay-2000" />
      </div>

      <LiquidGlass
        cornerRadius={32}
        blurAmount={0.06}
        displacementScale={50}
        padding="48px"
        className="max-w-lg text-center relative z-10"
      >
        <div className="space-y-6">
          <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center">
            <span className="text-4xl font-bold text-white">{message === "404" ? "?" : "!"}</span>
          </div>

          <div className="space-y-2">
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white">{message}</h1>
            <p className="text-lg text-gray-600 dark:text-gray-300">{details}</p>
          </div>

          {stack && (
            <div className="text-left">
              <pre className="p-4 bg-gray-900 rounded-xl overflow-x-auto">
                <code className="text-sm text-gray-300">{stack}</code>
              </pre>
            </div>
          )}

          <div className="flex justify-center gap-4">
            <a
              href="/"
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-colors"
            >
              Go Home
            </a>
            <button
              onClick={() => window.history.back()}
              className="px-6 py-3 bg-white/30 dark:bg-white/10 hover:bg-white/40 dark:hover:bg-white/20 text-gray-700 dark:text-gray-200 rounded-xl font-medium transition-colors"
            >
              Go Back
            </button>
          </div>
        </div>
      </LiquidGlass>
    </div>
  );
}
