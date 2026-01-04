import { Link } from "react-router";
import LiquidGlass from "liquid-glass-react";

export function meta() {
  return [
    { title: "Muelsyse CI - Modern CI/CD Platform" },
    { name: "description", content: "A modern, beautiful CI/CD platform with liquid glass UI" },
  ];
}

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 via-blue-50 to-purple-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-300 dark:bg-purple-900 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-30 animate-blob" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-300 dark:bg-blue-900 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-30 animate-blob animation-delay-2000" />
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-pink-300 dark:bg-pink-900 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-20 animate-blob animation-delay-4000" />
      </div>

      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 py-16">
        {/* Logo & Title */}
        <LiquidGlass
          cornerRadius={32}
          blurAmount={0.06}
          displacementScale={60}
          padding="32px"
          className="mb-8"
        >
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <span className="text-white font-bold text-3xl">M</span>
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Muelsyse CI</h1>
              <p className="text-gray-500 dark:text-gray-400">Modern CI/CD Platform</p>
            </div>
          </div>
        </LiquidGlass>

        {/* Main Content */}
        <LiquidGlass
          cornerRadius={32}
          blurAmount={0.05}
          displacementScale={50}
          padding="48px"
          className="max-w-2xl text-center"
        >
          <div className="space-y-6">
            <h2 className="text-4xl font-bold text-gray-900 dark:text-white">
              Build, Test, Deploy
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-purple-600">
                With Confidence
              </span>
            </h2>

            <p className="text-lg text-gray-600 dark:text-gray-300 max-w-lg mx-auto">
              A powerful, self-hosted CI/CD solution with a beautiful liquid glass interface.
              Automate your workflows with ease.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
              <Link
                to="/dashboard"
                className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-semibold text-lg transition-all duration-200 hover:scale-105 shadow-lg shadow-blue-500/30"
              >
                Go to Dashboard
              </Link>
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="px-8 py-4 bg-white/30 dark:bg-white/10 hover:bg-white/40 dark:hover:bg-white/20 text-gray-700 dark:text-gray-200 rounded-2xl font-semibold text-lg transition-all duration-200 hover:scale-105"
              >
                View on GitHub
              </a>
            </div>
          </div>
        </LiquidGlass>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12 max-w-5xl">
          {[
            {
              icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              ),
              title: "Fast Execution",
              description: "Parallel job execution with smart caching for lightning-fast builds.",
            },
            {
              icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              ),
              title: "Secure by Design",
              description: "Encrypted secrets, secure runners, and comprehensive audit logs.",
            },
            {
              icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                </svg>
              ),
              title: "Flexible Pipelines",
              description: "Define complex workflows with YAML. Supports any language or framework.",
            },
          ].map((feature, index) => (
            <LiquidGlass
              key={index}
              cornerRadius={24}
              blurAmount={0.06}
              displacementScale={40}
              padding="24px"
              className="text-center"
            >
              <div className="space-y-4">
                <div className="w-14 h-14 mx-auto rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center text-blue-600 dark:text-blue-400">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">{feature.title}</h3>
                <p className="text-gray-600 dark:text-gray-300">{feature.description}</p>
              </div>
            </LiquidGlass>
          ))}
        </div>

        {/* Footer */}
        <footer className="mt-16 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>Muelsyse CI - v0.1.0</p>
        </footer>
      </div>
    </div>
  );
}
