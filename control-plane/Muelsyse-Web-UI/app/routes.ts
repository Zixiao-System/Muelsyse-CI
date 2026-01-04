import {
  type RouteConfig,
  index,
  layout,
  route,
  prefix,
} from "@react-router/dev/routes";

export default [
  // Home page (welcome/landing)
  index("routes/home.tsx"),

  // Main app routes with layout
  layout("routes/_layout.tsx", [
    // Dashboard
    route("dashboard", "routes/dashboard.tsx"),

    // Pipelines
    ...prefix("pipelines", [
      index("routes/pipelines._index.tsx"),
      route(":id", "routes/pipelines.$id.tsx"),
    ]),

    // Executions
    ...prefix("executions", [
      index("routes/executions._index.tsx"),
      route(":id", "routes/executions.$id.tsx"),
    ]),

    // Runners
    route("runners", "routes/runners.tsx"),

    // Secrets
    route("secrets", "routes/secrets.tsx"),

    // Settings
    route("settings", "routes/settings.tsx"),
  ]),
] satisfies RouteConfig;
