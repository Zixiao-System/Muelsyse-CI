import LiquidGlass from "liquid-glass-react";

export function meta() {
  return [
    { title: "Settings | Muelsyse CI" },
    { name: "description", content: "Configure your workspace settings" },
  ];
}

export default function Settings() {
  return (
    <div className="space-y-6 max-w-4xl">
      {/* General Settings */}
      <LiquidGlass
        cornerRadius={24}
        blurAmount={0.05}
        displacementScale={45}
        padding="24px"
      >
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">General Settings</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">Basic configuration for your workspace</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Workspace Name
              </label>
              <input
                type="text"
                defaultValue="My Workspace"
                className="w-full px-4 py-2 bg-white/30 dark:bg-white/10 border border-gray-200/30 dark:border-gray-700/30 rounded-xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Default Branch
              </label>
              <input
                type="text"
                defaultValue="main"
                className="w-full px-4 py-2 bg-white/30 dark:bg-white/10 border border-gray-200/30 dark:border-gray-700/30 rounded-xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Timezone
              </label>
              <select className="w-full px-4 py-2 bg-white/30 dark:bg-white/10 border border-gray-200/30 dark:border-gray-700/30 rounded-xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50">
                <option value="UTC">UTC</option>
                <option value="America/New_York">Eastern Time (US)</option>
                <option value="America/Los_Angeles">Pacific Time (US)</option>
                <option value="Europe/London">London</option>
                <option value="Asia/Shanghai">Shanghai</option>
                <option value="Asia/Tokyo">Tokyo</option>
              </select>
            </div>
          </div>
        </div>
      </LiquidGlass>

      {/* Notifications */}
      <LiquidGlass
        cornerRadius={24}
        blurAmount={0.05}
        displacementScale={45}
        padding="24px"
      >
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Notifications</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">Configure how you receive alerts</p>
          </div>

          <div className="space-y-4">
            {[
              { label: "Email notifications", description: "Receive email alerts for pipeline status changes", checked: true },
              { label: "Slack integration", description: "Send notifications to Slack channels", checked: false },
              { label: "Failed builds only", description: "Only notify on failed pipeline executions", checked: true },
            ].map((item, index) => (
              <div key={index} className="flex items-start justify-between p-4 bg-white/20 dark:bg-white/5 rounded-xl">
                <div>
                  <h3 className="font-medium text-gray-900 dark:text-white">{item.label}</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{item.description}</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" defaultChecked={item.checked} className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-200 dark:bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
            ))}
          </div>
        </div>
      </LiquidGlass>

      {/* API Access */}
      <LiquidGlass
        cornerRadius={24}
        blurAmount={0.05}
        displacementScale={45}
        padding="24px"
      >
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">API Access</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">Manage API tokens for programmatic access</p>
          </div>

          <div className="space-y-4">
            <div className="p-4 bg-white/20 dark:bg-white/5 rounded-xl">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-medium text-gray-900 dark:text-white">Personal Access Token</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Created on Jan 15, 2024</p>
                </div>
                <button className="px-3 py-1.5 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg text-sm font-medium transition-colors">
                  Revoke
                </button>
              </div>
              <div className="flex items-center gap-2">
                <code className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm text-gray-600 dark:text-gray-300 font-mono">
                  muel_••••••••••••••••••••
                </code>
                <button className="px-3 py-2 bg-white/30 dark:bg-white/10 hover:bg-white/40 dark:hover:bg-white/20 text-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium transition-colors">
                  Copy
                </button>
              </div>
            </div>

            <button className="w-full px-4 py-3 border-2 border-dashed border-gray-300 dark:border-gray-600 hover:border-blue-500 dark:hover:border-blue-400 rounded-xl text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
              + Generate New Token
            </button>
          </div>
        </div>
      </LiquidGlass>

      {/* Danger Zone */}
      <LiquidGlass
        cornerRadius={24}
        blurAmount={0.05}
        displacementScale={45}
        padding="24px"
      >
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-red-600 dark:text-red-400">Danger Zone</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">Irreversible actions for your workspace</p>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 border border-red-200 dark:border-red-900/50 rounded-xl">
              <div>
                <h3 className="font-medium text-gray-900 dark:text-white">Delete Workspace</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">Permanently delete this workspace and all data</p>
              </div>
              <button className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-sm font-medium transition-colors">
                Delete
              </button>
            </div>
          </div>
        </div>
      </LiquidGlass>

      {/* Save Button */}
      <div className="flex justify-end">
        <LiquidGlass
          cornerRadius={12}
          blurAmount={0.08}
          displacementScale={30}
          padding="0"
        >
          <button className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-colors">
            Save Changes
          </button>
        </LiquidGlass>
      </div>
    </div>
  );
}
