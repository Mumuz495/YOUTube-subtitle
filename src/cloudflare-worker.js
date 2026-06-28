import { Container, getContainer } from "@cloudflare/containers";

export class SubtitleStudioContainer extends Container {
  defaultPort = 8765;
  sleepAfter = "15m";
}

function containerEnv(env) {
  const required = ["DEEPSEEK_API_KEY", "APP_PASSWORD"];
  const missing = required.filter((name) => !env[name]);
  if (missing.length) {
    return { missing, envVars: null };
  }

  return {
    missing: [],
    envVars: {
      HOST: "0.0.0.0",
      PORT: "8765",
      BROWSER_EXECUTABLE: "/usr/bin/chromium",
      PUBLIC_DEPLOYMENT: "1",
      ALLOW_CUSTOM_OUTPUT_DIR: "0",
      RATE_LIMIT_ENABLED: env.RATE_LIMIT_ENABLED || "1",
      RATE_LIMIT_MAX_REQUESTS: env.RATE_LIMIT_MAX_REQUESTS || "60",
      RATE_LIMIT_WINDOW_SECONDS: env.RATE_LIMIT_WINDOW_SECONDS || "600",
      OUTPUT_RETENTION_HOURS: env.OUTPUT_RETENTION_HOURS || "24",
      MAX_REQUEST_BYTES: env.MAX_REQUEST_BYTES || "8388608",
      APP_USERNAME: env.APP_USERNAME || "friend",
      APP_PASSWORD: env.APP_PASSWORD,
      DEEPSEEK_API_KEY: env.DEEPSEEK_API_KEY,
    },
  };
}

export default {
  async fetch(request, env) {
    const { missing, envVars } = containerEnv(env);
    if (missing.length) {
      return Response.json(
        {
          ok: false,
          error: `Missing required Cloudflare secret(s): ${missing.join(", ")}`,
        },
        { status: 500 },
      );
    }

    const container = getContainer(env.SUBTITLE_STUDIO_CONTAINER, "shared");
    await container.startAndWaitForPorts({
      ports: [8765],
      startOptions: { envVars },
      cancellationOptions: { portReadyTimeoutMS: 60_000 },
    });

    return container.fetch(request);
  },
};
