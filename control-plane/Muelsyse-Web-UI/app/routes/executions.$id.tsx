import { useParams, Link } from "react-router";
import LiquidGlass from "liquid-glass-react";

export function meta() {
  return [
    { title: "Execution Details | Muelsyse CI" },
    { name: "description", content: "View execution logs and status" },
  ];
}

// Mock data for demonstration
const executionData = {
  id: "exec-001",
  pipeline: "frontend-build",
  pipelineId: "pipeline-001",
  status: "success",
  duration: "2m 34s",
  startedAt: "2024-01-20 14:30:00",
  finishedAt: "2024-01-20 14:32:34",
  commit: "abc1234",
  commitMessage: "feat: add new dashboard component",
  branch: "main",
  author: "John Doe",
  runner: "runner-001",
  jobs: [
    {
      id: "job-001",
      name: "checkout",
      status: "success",
      duration: "5s",
      startedAt: "14:30:00",
      logs: [
        { time: "14:30:00", message: "Cloning repository..." },
        { time: "14:30:02", message: "Repository cloned successfully" },
        { time: "14:30:03", message: "Checking out branch: main" },
        { time: "14:30:05", message: "Checkout complete" },
      ],
    },
    {
      id: "job-002",
      name: "install",
      status: "success",
      duration: "45s",
      startedAt: "14:30:05",
      logs: [
        { time: "14:30:05", message: "Running npm install..." },
        { time: "14:30:20", message: "Installing dependencies..." },
        { time: "14:30:45", message: "Added 1247 packages" },
        { time: "14:30:50", message: "Install complete" },
      ],
    },
    {
      id: "job-003",
      name: "lint",
      status: "success",
      duration: "12s",
      startedAt: "14:30:50",
      logs: [
        { time: "14:30:50", message: "Running ESLint..." },
        { time: "14:31:02", message: "No linting errors found" },
      ],
    },
    {
      id: "job-004",
      name: "test",
      status: "success",
      duration: "1m 30s",
      startedAt: "14:31:02",
      logs: [
        { time: "14:31:02", message: "Running test suite..." },
        { time: "14:31:30", message: "Running 47 tests..." },
        { time: "14:32:00", message: "Tests: 47 passed, 0 failed" },
        { time: "14:32:32", message: "Test coverage: 87.5%" },
      ],
    },
    {
      id: "job-005",
      name: "build",
      status: "success",
      duration: "52s",
      startedAt: "14:32:32",
      logs: [
        { time: "14:32:32", message: "Building production bundle..." },
        { time: "14:33:00", message: "Optimizing assets..." },
        { time: "14:33:20", message: "Build complete: 2.3MB" },
        { time: "14:33:24", message: "Artifacts uploaded successfully" },
      ],
    },
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

function JobStatusIcon({ status }: { status: string }) {
  if (status === "success") {
    return (
      <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    );
  }
  if (status === "failed") {
    return (
      <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    );
  }
  if (status === "running") {
    return (
      <svg className="w-5 h-5 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
      </svg>
    );
  }
  return (
    <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

export default function ExecutionDetail() {
  const { id } = useParams();

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
        <Link to="/executions" className="hover:text-blue-600 dark:hover:text-blue-400">
          Executions
        </Link>
        <span>/</span>
        <span className="text-gray-900 dark:text-white">{executionData.id}</span>
      </nav>

      {/* Header */}
      <LiquidGlass
        cornerRadius={24}
        blurAmount={0.05}
        displacementScale={45}
        padding="24px"
      >
        <div className="flex items-start justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Link
                to={`/pipelines/${executionData.pipelineId}`}
                className="text-2xl font-bold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400"
              >
                {executionData.pipeline}
              </Link>
              <StatusBadge status={executionData.status} />
            </div>
            <p className="text-gray-600 dark:text-gray-300">{executionData.commitMessage}</p>
            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
                {executionData.branch}
              </span>
              <span className="flex items-center gap-1">
                <code className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs">
                  {executionData.commit}
                </code>
              </span>
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                {executionData.author}
              </span>
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {executionData.duration}
              </span>
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" />
                </svg>
                Runner: {executionData.runner}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors">
              Re-run
            </button>
            <button className="px-4 py-2 bg-white/30 dark:bg-white/10 hover:bg-white/40 dark:hover:bg-white/20 text-gray-700 dark:text-gray-200 rounded-xl text-sm font-medium transition-colors">
              Download Logs
            </button>
          </div>
        </div>
      </LiquidGlass>

      {/* Jobs Timeline */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Jobs</h2>
        {executionData.jobs.map((job) => (
          <LiquidGlass
            key={job.id}
            cornerRadius={20}
            blurAmount={0.05}
            displacementScale={40}
            padding="20px"
          >
            <details className="group">
              <summary className="flex items-center justify-between cursor-pointer list-none">
                <div className="flex items-center gap-3">
                  <JobStatusIcon status={job.status} />
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">{job.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Started at {job.startedAt} - Duration: {job.duration}
                    </p>
                  </div>
                </div>
                <svg
                  className="w-5 h-5 text-gray-500 transition-transform group-open:rotate-180"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </summary>
              <div className="mt-4 pt-4 border-t border-gray-200/30 dark:border-gray-700/30">
                <div className="bg-gray-900 rounded-xl p-4 font-mono text-sm overflow-x-auto">
                  {job.logs.map((log, index) => (
                    <div key={index} className="flex gap-4 text-gray-300">
                      <span className="text-gray-500 select-none">{log.time}</span>
                      <span>{log.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            </details>
          </LiquidGlass>
        ))}
      </div>
    </div>
  );
}
