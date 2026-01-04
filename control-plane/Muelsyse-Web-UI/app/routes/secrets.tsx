import LiquidGlass from "liquid-glass-react";

export function meta() {
  return [
    { title: "Secrets | Muelsyse CI" },
    { name: "description", content: "Manage environment secrets" },
  ];
}

// Mock data for demonstration
const secrets = [
  {
    id: "secret-001",
    name: "DOCKER_REGISTRY_TOKEN",
    scope: "organization",
    lastUpdated: "2024-01-15",
    usedIn: ["frontend-build", "backend-build"],
  },
  {
    id: "secret-002",
    name: "AWS_ACCESS_KEY_ID",
    scope: "organization",
    lastUpdated: "2024-01-10",
    usedIn: ["deploy-staging", "deploy-production"],
  },
  {
    id: "secret-003",
    name: "AWS_SECRET_ACCESS_KEY",
    scope: "organization",
    lastUpdated: "2024-01-10",
    usedIn: ["deploy-staging", "deploy-production"],
  },
  {
    id: "secret-004",
    name: "NPM_TOKEN",
    scope: "repository",
    lastUpdated: "2024-01-08",
    usedIn: ["frontend-build"],
  },
  {
    id: "secret-005",
    name: "SLACK_WEBHOOK_URL",
    scope: "organization",
    lastUpdated: "2024-01-05",
    usedIn: ["notify-slack"],
  },
];

export default function Secrets() {
  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <input
            type="text"
            placeholder="Search secrets..."
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
            + Add Secret
          </button>
        </LiquidGlass>
      </div>

      {/* Warning Banner */}
      <LiquidGlass
        cornerRadius={16}
        blurAmount={0.06}
        displacementScale={35}
        padding="16px"
      >
        <div className="flex items-start gap-3">
          <svg className="w-5 h-5 text-yellow-500 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-white">Security Notice</h3>
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
              Secrets are encrypted at rest and never exposed in logs. Only authorized pipelines can access secrets within their scope.
            </p>
          </div>
        </div>
      </LiquidGlass>

      {/* Secrets List */}
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
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Scope</th>
                <th className="pb-3 font-medium">Used In</th>
                <th className="pb-3 font-medium">Last Updated</th>
                <th className="pb-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200/30 dark:divide-gray-700/30">
              {secrets.map((secret) => (
                <tr key={secret.id} className="hover:bg-white/10 transition-colors">
                  <td className="py-4">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                      <code className="text-gray-900 dark:text-white font-medium">{secret.name}</code>
                    </div>
                  </td>
                  <td className="py-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      secret.scope === "organization"
                        ? "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400"
                        : "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
                    }`}>
                      {secret.scope}
                    </span>
                  </td>
                  <td className="py-4">
                    <div className="flex flex-wrap gap-1">
                      {secret.usedIn.slice(0, 2).map((pipeline) => (
                        <span
                          key={pipeline}
                          className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 rounded text-xs"
                        >
                          {pipeline}
                        </span>
                      ))}
                      {secret.usedIn.length > 2 && (
                        <span className="px-2 py-0.5 text-gray-500 text-xs">
                          +{secret.usedIn.length - 2} more
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-4 text-gray-500 dark:text-gray-400 text-sm">{secret.lastUpdated}</td>
                  <td className="py-4">
                    <div className="flex items-center gap-2">
                      <button className="px-3 py-1.5 bg-white/20 dark:bg-white/10 hover:bg-white/30 dark:hover:bg-white/20 text-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium transition-colors">
                        Update
                      </button>
                      <button className="p-1.5 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </LiquidGlass>
    </div>
  );
}
