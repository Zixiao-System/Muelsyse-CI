import LiquidGlass from "liquid-glass-react";

export function meta() {
  return [
    { title: "Dashboard | Muelsyse CI" },
    { name: "description", content: "CI/CD Dashboard Overview" },
  ];
}

// Mock data for demonstration
const stats = [
  { label: "Total Pipelines", value: "12", change: "+2", trend: "up" },
  { label: "Executions Today", value: "47", change: "+15", trend: "up" },
  { label: "Success Rate", value: "94.2%", change: "+1.2%", trend: "up" },
  { label: "Active Runners", value: "5", change: "0", trend: "neutral" },
];

const recentExecutions = [
  { id: "exec-001", pipeline: "frontend-build", status: "success", duration: "2m 34s", time: "5 min ago" },
  { id: "exec-002", pipeline: "api-tests", status: "running", duration: "1m 12s", time: "8 min ago" },
  { id: "exec-003", pipeline: "deploy-staging", status: "failed", duration: "4m 56s", time: "15 min ago" },
  { id: "exec-004", pipeline: "backend-build", status: "success", duration: "3m 21s", time: "22 min ago" },
];

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

export default function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, index) => (
          <LiquidGlass
            key={index}
            cornerRadius={20}
            blurAmount={0.06}
            displacementScale={40}
            padding="20px"
          >
            <div className="space-y-2">
              <p className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</p>
              <div className="flex items-end justify-between">
                <p className="text-3xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
                <span className={`text-sm font-medium ${
                  stat.trend === "up" ? "text-green-600 dark:text-green-400" :
                  stat.trend === "down" ? "text-red-600 dark:text-red-400" :
                  "text-gray-500"
                }`}>
                  {stat.change}
                </span>
              </div>
            </div>
          </LiquidGlass>
        ))}
      </div>

      {/* Recent Executions */}
      <LiquidGlass
        cornerRadius={24}
        blurAmount={0.05}
        displacementScale={45}
        padding="24px"
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Executions</h2>
            <a href="/executions" className="text-sm text-blue-600 dark:text-blue-400 hover:underline">
              View all
            </a>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-gray-500 dark:text-gray-400 border-b border-gray-200/30 dark:border-gray-700/30">
                  <th className="pb-3 font-medium">Pipeline</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Duration</th>
                  <th className="pb-3 font-medium">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200/30 dark:divide-gray-700/30">
                {recentExecutions.map((execution) => (
                  <tr key={execution.id} className="hover:bg-white/10 transition-colors">
                    <td className="py-3">
                      <a
                        href={`/executions/${execution.id}`}
                        className="text-gray-900 dark:text-white font-medium hover:text-blue-600 dark:hover:text-blue-400"
                      >
                        {execution.pipeline}
                      </a>
                    </td>
                    <td className="py-3">
                      <StatusBadge status={execution.status} />
                    </td>
                    <td className="py-3 text-gray-600 dark:text-gray-300">{execution.duration}</td>
                    <td className="py-3 text-gray-500 dark:text-gray-400">{execution.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </LiquidGlass>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <LiquidGlass
          cornerRadius={20}
          blurAmount={0.06}
          displacementScale={40}
          padding="20px"
        >
          <div className="space-y-3">
            <h3 className="font-semibold text-gray-900 dark:text-white">Quick Actions</h3>
            <div className="flex flex-wrap gap-2">
              <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors">
                New Pipeline
              </button>
              <button className="px-4 py-2 bg-white/30 dark:bg-white/10 hover:bg-white/40 dark:hover:bg-white/20 text-gray-900 dark:text-white rounded-xl text-sm font-medium transition-colors">
                Add Runner
              </button>
            </div>
          </div>
        </LiquidGlass>

        <LiquidGlass
          cornerRadius={20}
          blurAmount={0.06}
          displacementScale={40}
          padding="20px"
        >
          <div className="space-y-3">
            <h3 className="font-semibold text-gray-900 dark:text-white">System Status</h3>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-sm text-gray-600 dark:text-gray-300">All systems operational</span>
            </div>
          </div>
        </LiquidGlass>
      </div>
    </div>
  );
}
