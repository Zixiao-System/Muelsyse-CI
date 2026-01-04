import { useParams, Link } from "react-router";
import LiquidGlass from "liquid-glass-react";

export function meta() {
  return [
    { title: "Pipeline Details | Muelsyse CI" },
    { name: "description", content: "View pipeline configuration and history" },
  ];
}

// Mock data for demonstration
const pipelineData = {
  id: "pipeline-001",
  name: "frontend-build",
  description: "Build and test React frontend application",
  status: "success",
  branch: "main",
  trigger: "push",
  createdAt: "2024-01-15",
  lastRun: "5 min ago",
  totalRuns: 142,
  successRate: 94.5,
  avgDuration: "3m 24s",
  stages: [
    { name: "checkout", status: "success", duration: "5s" },
    { name: "install", status: "success", duration: "45s" },
    { name: "lint", status: "success", duration: "12s" },
    { name: "test", status: "success", duration: "1m 30s" },
    { name: "build", status: "success", duration: "52s" },
  ],
  recentExecutions: [
    { id: "exec-001", status: "success", duration: "2m 34s", time: "5 min ago", commit: "abc1234" },
    { id: "exec-002", status: "success", duration: "2m 41s", time: "1 hour ago", commit: "def5678" },
    { id: "exec-003", status: "failed", duration: "1m 12s", time: "2 hours ago", commit: "ghi9012" },
    { id: "exec-004", status: "success", duration: "2m 38s", time: "3 hours ago", commit: "jkl3456" },
  ],
};

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    success: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
    running: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
    failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
    pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}>
      {status}
    </span>
  );
}

function StageIndicator({ status }: { status: string }) {
  const colors: Record<string, string> = {
    success: "bg-green-500",
    running: "bg-blue-500 animate-pulse",
    failed: "bg-red-500",
    pending: "bg-gray-400",
  };

  return <span className={`w-4 h-4 rounded-full ${colors[status] || colors.pending}`} />;
}

export default function PipelineDetail() {
  const { id } = useParams();

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
        <Link to="/pipelines" className="hover:text-blue-600 dark:hover:text-blue-400">
          Pipelines
        </Link>
        <span>/</span>
        <span className="text-gray-900 dark:text-white">{pipelineData.name}</span>
      </nav>

      {/* Header */}
      <LiquidGlass
        cornerRadius={24}
        blurAmount={0.05}
        displacementScale={45}
        padding="24px"
      >
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{pipelineData.name}</h1>
              <StatusBadge status={pipelineData.status} />
            </div>
            <p className="text-gray-600 dark:text-gray-300">{pipelineData.description}</p>
            <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
              <span>Branch: {pipelineData.branch}</span>
              <span>Trigger: {pipelineData.trigger}</span>
              <span>Created: {pipelineData.createdAt}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors">
              Run Pipeline
            </button>
            <button className="px-4 py-2 bg-white/30 dark:bg-white/10 hover:bg-white/40 dark:hover:bg-white/20 text-gray-700 dark:text-gray-200 rounded-xl text-sm font-medium transition-colors">
              Edit
            </button>
          </div>
        </div>
      </LiquidGlass>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: "Total Runs", value: pipelineData.totalRuns.toString() },
          { label: "Success Rate", value: `${pipelineData.successRate}%` },
          { label: "Avg Duration", value: pipelineData.avgDuration },
          { label: "Last Run", value: pipelineData.lastRun },
        ].map((stat, index) => (
          <LiquidGlass
            key={index}
            cornerRadius={16}
            blurAmount={0.06}
            displacementScale={35}
            padding="16px"
          >
            <p className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
          </LiquidGlass>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pipeline Stages */}
        <LiquidGlass
          cornerRadius={24}
          blurAmount={0.05}
          displacementScale={40}
          padding="24px"
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Pipeline Stages</h2>
          <div className="space-y-3">
            {pipelineData.stages.map((stage, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-white/20 dark:bg-white/5 rounded-xl"
              >
                <div className="flex items-center gap-3">
                  <StageIndicator status={stage.status} />
                  <span className="font-medium text-gray-900 dark:text-white">{stage.name}</span>
                </div>
                <span className="text-sm text-gray-500 dark:text-gray-400">{stage.duration}</span>
              </div>
            ))}
          </div>
        </LiquidGlass>

        {/* Recent Executions */}
        <LiquidGlass
          cornerRadius={24}
          blurAmount={0.05}
          displacementScale={40}
          padding="24px"
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recent Executions</h2>
          <div className="space-y-3">
            {pipelineData.recentExecutions.map((execution) => (
              <Link
                key={execution.id}
                to={`/executions/${execution.id}`}
                className="flex items-center justify-between p-3 bg-white/20 dark:bg-white/5 rounded-xl hover:bg-white/30 dark:hover:bg-white/10 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <StatusBadge status={execution.status} />
                  <div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {execution.commit}
                    </span>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{execution.time}</p>
                  </div>
                </div>
                <span className="text-sm text-gray-500 dark:text-gray-400">{execution.duration}</span>
              </Link>
            ))}
          </div>
        </LiquidGlass>
      </div>
    </div>
  );
}
