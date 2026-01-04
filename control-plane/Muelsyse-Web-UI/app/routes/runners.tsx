import LiquidGlass from "liquid-glass-react";

export function meta() {
  return [
    { title: "Runners | Muelsyse CI" },
    { name: "description", content: "Manage your build runners" },
  ];
}

// Mock data for demonstration
const runners = [
  {
    id: "runner-001",
    name: "linux-runner-1",
    status: "online",
    platform: "Linux",
    arch: "x86_64",
    version: "1.0.0",
    lastSeen: "Just now",
    labels: ["docker", "node", "go"],
    currentJob: "frontend-build #142",
  },
  {
    id: "runner-002",
    name: "linux-runner-2",
    status: "online",
    platform: "Linux",
    arch: "x86_64",
    version: "1.0.0",
    lastSeen: "Just now",
    labels: ["docker", "node"],
    currentJob: null,
  },
  {
    id: "runner-003",
    name: "macos-runner-1",
    status: "offline",
    platform: "macOS",
    arch: "arm64",
    version: "1.0.0",
    lastSeen: "2 hours ago",
    labels: ["ios", "swift", "xcode"],
    currentJob: null,
  },
  {
    id: "runner-004",
    name: "windows-runner-1",
    status: "online",
    platform: "Windows",
    arch: "x86_64",
    version: "0.9.5",
    lastSeen: "Just now",
    labels: ["dotnet", "msbuild"],
    currentJob: null,
  },
];

function StatusIndicator({ status }: { status: string }) {
  const colors: Record<string, string> = {
    online: "bg-green-500",
    offline: "bg-gray-400",
    busy: "bg-yellow-500",
  };

  return (
    <span className={`w-3 h-3 rounded-full ${colors[status] || colors.offline} ${status === "online" ? "animate-pulse" : ""}`} />
  );
}

function PlatformIcon({ platform }: { platform: string }) {
  if (platform === "Linux") {
    return (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12.504 0c-.155 0-.315.008-.48.021-4.226.333-3.105 4.807-3.17 6.298-.076 1.092-.3 1.953-1.05 3.02-.885 1.051-2.127 2.75-2.716 4.521-.278.832-.41 1.684-.287 2.489a.424.424 0 00-.11.135c-.26.268-.45.6-.663.839-.199.199-.485.267-.797.4-.313.136-.658.269-.864.68-.09.189-.136.394-.132.602 0 .199.027.4.055.536.058.399.116.728.04.97-.249.68-.28 1.145-.106 1.484.174.334.535.47.94.601.81.2 1.91.135 2.774.6.926.466 1.866.67 2.616.47.526-.116.97-.464 1.208-.946.587-.003 1.23-.269 2.26-.334.699-.058 1.574.267 2.577.2.025.134.063.198.114.333l.003.003c.391.778 1.113 1.132 1.884 1.071.771-.06 1.592-.536 2.257-1.306.631-.765 1.683-1.084 2.378-1.503.348-.199.629-.469.649-.853.023-.4-.2-.811-.714-1.376v-.097l-.003-.003c-.17-.2-.25-.535-.338-.926-.085-.401-.182-.786-.492-1.046h-.003c-.059-.054-.123-.067-.188-.135a.357.357 0 00-.19-.064c.431-1.278.264-2.55-.173-3.694-.533-1.41-1.465-2.638-2.175-3.483-.796-1.005-1.576-1.957-1.56-3.368.026-2.152.236-6.133-3.544-6.139zm.529 3.405h.013c.213 0 .396.062.584.198.19.135.33.332.438.533.105.259.158.459.166.724 0-.02.006-.04.006-.06v.105a.086.086 0 01-.004-.021l-.004-.024a1.807 1.807 0 01-.15.706.953.953 0 01-.213.335.71.71 0 00-.088-.042c-.104-.045-.198-.064-.284-.133a1.312 1.312 0 00-.22-.066c.05-.06.146-.133.183-.198.053-.128.082-.264.088-.402v-.02a1.21 1.21 0 00-.061-.4c-.045-.134-.101-.2-.183-.333-.084-.066-.167-.132-.267-.132h-.016c-.093 0-.176.03-.262.132a.8.8 0 00-.205.334 1.18 1.18 0 00-.09.4v.019c.002.089.008.179.02.267-.193-.067-.438-.135-.607-.202a1.635 1.635 0 01-.018-.2v-.02a1.772 1.772 0 01.15-.768c.082-.22.232-.406.43-.533a.985.985 0 01.594-.2zm-2.962.059h.036c.142 0 .27.048.399.135.146.129.264.288.344.465.09.199.14.4.153.667l.004.073v.052a1.63 1.63 0 01-.09.645c-.072.2-.18.4-.322.465a.416.416 0 01-.22.065c-.065 0-.141-.023-.226-.067-.09-.043-.166-.087-.217-.135a.956.956 0 01-.176-.338 1.508 1.508 0 01-.09-.4v-.067a1.57 1.57 0 01.09-.645c.072-.199.18-.332.322-.398a.478.478 0 01.213-.066z" />
      </svg>
    );
  }
  if (platform === "macOS") {
    return (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm0 18c-4.418 0-8-3.582-8-8s3.582-8 8-8 8 3.582 8 8-3.582 8-8 8zm-1-13h2v6h-2V7zm0 8h2v2h-2v-2z" />
      </svg>
    );
  }
  if (platform === "Windows") {
    return (
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M0 3.449L9.75 2.1v9.451H0m10.949-9.602L24 0v11.4H10.949M0 12.6h9.75v9.451L0 20.699M10.949 12.6H24V24l-12.9-1.801" />
      </svg>
    );
  }
  return null;
}

export default function Runners() {
  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {runners.filter((r) => r.status === "online").length} of {runners.length} runners online
          </span>
        </div>
        <LiquidGlass
          cornerRadius={12}
          blurAmount={0.08}
          displacementScale={30}
          padding="0"
        >
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors">
            + Register Runner
          </button>
        </LiquidGlass>
      </div>

      {/* Runners Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {runners.map((runner) => (
          <LiquidGlass
            key={runner.id}
            cornerRadius={20}
            blurAmount={0.05}
            displacementScale={40}
            padding="20px"
          >
            <div className="space-y-4">
              {/* Header */}
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <StatusIndicator status={runner.status} />
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">{runner.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Last seen: {runner.lastSeen}
                    </p>
                  </div>
                </div>
                <button className="p-2 rounded-lg hover:bg-white/20 dark:hover:bg-white/10 transition-colors">
                  <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                  </svg>
                </button>
              </div>

              {/* Info */}
              <div className="flex items-center gap-6 text-sm">
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                  <PlatformIcon platform={runner.platform} />
                  <span>{runner.platform}</span>
                </div>
                <div className="text-gray-600 dark:text-gray-300">
                  {runner.arch}
                </div>
                <div className="text-gray-500 dark:text-gray-400">
                  v{runner.version}
                </div>
              </div>

              {/* Labels */}
              <div className="flex flex-wrap gap-2">
                {runner.labels.map((label) => (
                  <span
                    key={label}
                    className="px-2 py-1 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg text-xs"
                  >
                    {label}
                  </span>
                ))}
              </div>

              {/* Current Job */}
              {runner.currentJob && (
                <div className="pt-3 border-t border-gray-200/30 dark:border-gray-700/30">
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Currently running:{" "}
                    <span className="text-blue-600 dark:text-blue-400 font-medium">
                      {runner.currentJob}
                    </span>
                  </p>
                </div>
              )}
            </div>
          </LiquidGlass>
        ))}
      </div>
    </div>
  );
}
