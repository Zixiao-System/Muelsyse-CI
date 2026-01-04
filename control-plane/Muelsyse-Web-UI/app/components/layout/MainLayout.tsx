import { Outlet, useLocation } from "react-router";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

// Map routes to page titles
const routeTitles: Record<string, { title: string; subtitle?: string }> = {
  "/dashboard": { title: "Dashboard", subtitle: "Overview of your CI/CD pipelines" },
  "/pipelines": { title: "Pipelines", subtitle: "Manage your build pipelines" },
  "/executions": { title: "Executions", subtitle: "View pipeline execution history" },
  "/runners": { title: "Runners", subtitle: "Manage your build runners" },
  "/secrets": { title: "Secrets", subtitle: "Manage environment secrets" },
  "/settings": { title: "Settings", subtitle: "Configure your workspace" },
};

function getPageInfo(pathname: string): { title: string; subtitle?: string } {
  // Check for exact match first
  if (routeTitles[pathname]) {
    return routeTitles[pathname];
  }

  // Check for dynamic routes
  if (pathname.startsWith("/pipelines/")) {
    return { title: "Pipeline Details", subtitle: "View and manage this pipeline" };
  }
  if (pathname.startsWith("/executions/")) {
    return { title: "Execution Details", subtitle: "View execution logs and status" };
  }

  // Default
  return { title: "Muelsyse CI", subtitle: "CI/CD Platform" };
}

export function MainLayout() {
  const location = useLocation();
  const { title, subtitle } = getPageInfo(location.pathname);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 via-blue-50 to-purple-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-300 dark:bg-purple-900 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-30 animate-blob" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-300 dark:bg-blue-900 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-30 animate-blob animation-delay-2000" />
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-pink-300 dark:bg-pink-900 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-20 animate-blob animation-delay-4000" />
      </div>

      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="ml-64 min-h-screen relative">
        <Header title={title} subtitle={subtitle} />

        <main className="px-6 pb-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
