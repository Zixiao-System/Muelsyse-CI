import { Link } from "react-router";
import LiquidGlass from "liquid-glass-react";

export function meta() {
  return [
    { title: "Executions | Muelsyse CI" },
    { name: "description", content: "View pipeline execution history" },
  ];
}

// Mock data for demonstration
const executions = [
  {
    id: "exec-001",
    pipeline: "frontend-build",
    pipelineId: "pipeline-001",
    status: "success",
    duration: "2m 34s",
    startedAt: "2024-01-20 14:30:00",
    commit: "abc1234",
    branch: "main",
    author: "John Doe",
  },
  {
    id: "exec-002",
    pipeline: "api-tests",
    pipelineId: "pipeline-002",
    status: "running",
    duration: "1m 12s",
    startedAt: "2024-01-20 14:28:00",
    commit: "def5678",
    branch: "develop",
    author: "Jane Smith",
  },
  {
    id: "exec-003",
    pipeline: "deploy-staging",
    pipelineId: "pipeline-003",
    status: "failed",
    duration: "4m 56s",
    startedAt: "2024-01-20 14:15:00",
    commit: "ghi9012",
    branch: "main",
    author: "Bob Wilson",
  },
  {
    id: "exec-004",
    pipeline: "backend-build",
    pipelineId: "pipeline-004",
    status: "success",
    duration: "3m 21s",
    startedAt: "2024-01-20 14:00:00",
    commit: "jkl3456",
    branch: "main",
    author: "Alice Brown",
  },
  {
    id: "exec-005",
    pipeline: "security-scan",
    pipelineId: "pipeline-005",
    status: "success",
    duration: "5m 12s",
    startedAt: "2024-01-20 13:45:00",
    commit: "mno7890",
    branch: "main",
    author: "Charlie Davis",
  },
];

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    success: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
    running: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
    failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
    pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
    cancelled: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}>
      {status}
    </span>
  );
}

export default function ExecutionsIndex() {
  return (
    <div className="space-y-6">
      {/* Filters */}
      <LiquidGlass
        cornerRadius={16}
        blurAmount={0.05}
        displacementScale={35}
        padding="16px"
      >
        <div className="flex flex-wrap items-center gap-4">
          <input
            type="text"
            placeholder="Search executions..."
            className="px-4 py-2 bg-white/30 dark:bg-white/10 border border-gray-200/30 dark:border-gray-700/30 rounded-xl text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 min-w-[200px]"
          />
          <select className="px-4 py-2 bg-white/30 dark:bg-white/10 border border-gray-200/30 dark:border-gray-700/30 rounded-xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50">
            <option value="">All Status</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
            <option value="pending">Pending</option>
          </select>
          <select className="px-4 py-2 bg-white/30 dark:bg-white/10 border border-gray-200/30 dark:border-gray-700/30 rounded-xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50">
            <option value="">All Pipelines</option>
            <option value="frontend-build">frontend-build</option>
            <option value="api-tests">api-tests</option>
            <option value="deploy-staging">deploy-staging</option>
          </select>
        </div>
      </LiquidGlass>

      {/* Executions List */}
      <LiquidGlass
        cornerRadius={24}
        blurAmount={0.05}
        displacementScale={45}
        padding="24px"
      >
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-sm text-gray-500 dark:text-gray-400 border-b border-gray-200/30 dark:border-gray-700/30">
                <th className="pb-3 font-medium">Pipeline</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Commit</th>
                <th className="pb-3 font-medium">Branch</th>
                <th className="pb-3 font-medium">Duration</th>
                <th className="pb-3 font-medium">Started</th>
                <th className="pb-3 font-medium">Author</th>
                <th className="pb-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200/30 dark:divide-gray-700/30">
              {executions.map((execution) => (
                <tr key={execution.id} className="hover:bg-white/10 transition-colors">
                  <td className="py-4">
                    <Link
                      to={`/pipelines/${execution.pipelineId}`}
                      className="text-gray-900 dark:text-white font-medium hover:text-blue-600 dark:hover:text-blue-400"
                    >
                      {execution.pipeline}
                    </Link>
                  </td>
                  <td className="py-4">
                    <StatusBadge status={execution.status} />
                  </td>
                  <td className="py-4">
                    <code className="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-sm text-gray-700 dark:text-gray-300">
                      {execution.commit}
                    </code>
                  </td>
                  <td className="py-4 text-gray-600 dark:text-gray-300">{execution.branch}</td>
                  <td className="py-4 text-gray-600 dark:text-gray-300">{execution.duration}</td>
                  <td className="py-4 text-gray-500 dark:text-gray-400 text-sm">{execution.startedAt}</td>
                  <td className="py-4 text-gray-600 dark:text-gray-300">{execution.author}</td>
                  <td className="py-4">
                    <Link
                      to={`/executions/${execution.id}`}
                      className="px-3 py-1.5 bg-white/20 dark:bg-white/10 hover:bg-white/30 dark:hover:bg-white/20 text-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium transition-colors"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-200/30 dark:border-gray-700/30">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Showing 1 to 5 of 47 executions
          </p>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1.5 bg-white/20 dark:bg-white/10 hover:bg-white/30 dark:hover:bg-white/20 text-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium transition-colors disabled:opacity-50" disabled>
              Previous
            </button>
            <button className="px-3 py-1.5 bg-white/20 dark:bg-white/10 hover:bg-white/30 dark:hover:bg-white/20 text-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium transition-colors">
              Next
            </button>
          </div>
        </div>
      </LiquidGlass>
    </div>
  );
}
