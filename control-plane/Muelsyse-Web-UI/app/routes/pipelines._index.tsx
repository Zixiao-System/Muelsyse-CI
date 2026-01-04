import { Link } from "react-router";
import LiquidGlass from "liquid-glass-react";

export function meta() {
  return [
    { title: "Pipelines | Muelsyse CI" },
    { name: "description", content: "Manage your CI/CD pipelines" },
  ];
}

// Mock data for demonstration
const pipelines = [
  {
    id: "pipeline-001",
    name: "frontend-build",
    description: "Build and test React frontend application",
    lastRun: "5 min ago",
    status: "success",
    runs: 142,
    branch: "main",
  },
  {
    id: "pipeline-002",
    name: "api-tests",
    description: "Run API integration tests",
    lastRun: "12 min ago",
    status: "running",
    runs: 89,
    branch: "develop",
  },
  {
    id: "pipeline-003",
    name: "deploy-staging",
    description: "Deploy to staging environment",
    lastRun: "1 hour ago",
    status: "failed",
    runs: 67,
    branch: "main",
  },
  {
    id: "pipeline-004",
    name: "backend-build",
    description: "Build Go backend services",
    lastRun: "2 hours ago",
    status: "success",
    runs: 234,
    branch: "main",
  },
  {
    id: "pipeline-005",
    name: "security-scan",
    description: "Run security vulnerability scans",
    lastRun: "3 hours ago",
    status: "success",
    runs: 45,
    branch: "main",
  },
];

function StatusIndicator({ status }: { status: string }) {
  const colors: Record<string, string> = {
    success: "bg-green-500",
    running: "bg-blue-500 animate-pulse",
    failed: "bg-red-500",
    pending: "bg-yellow-500",
  };

  return <span className={`w-3 h-3 rounded-full ${colors[status] || colors.pending}`} />;
}

export default function PipelinesIndex() {
  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <input
            type="text"
            placeholder="Search pipelines..."
            className="px-4 py-2 bg-white/30 dark:bg-white/10 border border-gray-200/30 dark:border-gray-700/30 rounded-xl text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          />
        </div>
        <LiquidGlass
          cornerRadius={12}
          blurAmount={0.08}
          displacementScale={30}
          padding="0"
        >
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors">
            + New Pipeline
          </button>
        </LiquidGlass>
      </div>

      {/* Pipelines Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {pipelines.map((pipeline) => (
          <Link key={pipeline.id} to={`/pipelines/${pipeline.id}`}>
            <LiquidGlass
              cornerRadius={20}
              blurAmount={0.05}
              displacementScale={40}
              padding="20px"
              className="h-full hover:scale-[1.02] transition-transform duration-200"
            >
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <StatusIndicator status={pipeline.status} />
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-white">{pipeline.name}</h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">{pipeline.description}</p>
                    </div>
                  </div>
                  <button
                    className="p-2 rounded-lg hover:bg-white/20 dark:hover:bg-white/10 transition-colors"
                    onClick={(e) => e.preventDefault()}
                  >
                    <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                    </svg>
                  </button>
                </div>

                {/* Stats */}
                <div className="flex items-center gap-6 text-sm">
                  <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{pipeline.lastRun}</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    <span>{pipeline.runs} runs</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                    <span>{pipeline.branch}</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-2 border-t border-gray-200/30 dark:border-gray-700/30">
                  <button
                    className="flex-1 px-3 py-2 bg-blue-600/80 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
                    onClick={(e) => e.preventDefault()}
                  >
                    Run Now
                  </button>
                  <button
                    className="px-3 py-2 bg-white/20 dark:bg-white/10 hover:bg-white/30 dark:hover:bg-white/20 text-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium transition-colors"
                    onClick={(e) => e.preventDefault()}
                  >
                    Edit
                  </button>
                </div>
              </div>
            </LiquidGlass>
          </Link>
        ))}
      </div>
    </div>
  );
}
