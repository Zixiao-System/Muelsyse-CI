import LiquidGlass from "liquid-glass-react";
import { ClientOnly } from "../ClientOnly";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const headerContent = (
    <div className="flex items-center justify-between">
      {/* Page Title */}
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
          {title}
        </h1>
        {subtitle && (
          <p className="text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>
        )}
      </div>

      {/* Right Section - User Actions */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <button
          className="p-2 rounded-xl text-gray-600 dark:text-gray-300 hover:bg-white/20 dark:hover:bg-white/5 transition-colors"
          aria-label="Notifications"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
        </button>

        {/* User Avatar / Login Button */}
        <ClientOnly
          fallback={
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/20 backdrop-blur">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-400 to-blue-500 flex items-center justify-center">
                <span className="text-white text-sm font-medium">U</span>
              </div>
              <span className="text-sm font-medium hidden sm:block text-gray-700 dark:text-gray-200">User</span>
            </div>
          }
        >
          <LiquidGlass
            cornerRadius={100}
            blurAmount={0.08}
            displacementScale={30}
            padding="2px"
          >
            <button
              className="flex items-center gap-2 px-3 py-1.5 rounded-full text-gray-700 dark:text-gray-200 hover:bg-white/20 transition-colors"
              aria-label="User menu"
            >
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-400 to-blue-500 flex items-center justify-center">
                <span className="text-white text-sm font-medium">U</span>
              </div>
              <span className="text-sm font-medium hidden sm:block">User</span>
              <svg className="w-4 h-4 hidden sm:block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </LiquidGlass>
        </ClientOnly>
      </div>
    </div>
  );

  return (
    <header className="sticky top-0 z-40 px-4 py-4">
      <ClientOnly
        fallback={
          <div className="bg-white/20 dark:bg-gray-900/20 backdrop-blur-lg rounded-2xl px-5 py-3">
            {headerContent}
          </div>
        }
      >
        <LiquidGlass
          cornerRadius={16}
          blurAmount={0.05}
          displacementScale={40}
          padding="12px 20px"
        >
          {headerContent}
        </LiquidGlass>
      </ClientOnly>
    </header>
  );
}
