import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const nextBin = require.resolve("next/dist/bin/next");
const port = Number(process.env.LOCALIZED_404_TEST_PORT ?? 4317);
const origin = `http://127.0.0.1:${port}`;
const server = spawn(process.execPath, [nextBin, "start", "-p", String(port)], {
  env: process.env,
  stdio: ["ignore", "pipe", "pipe"],
});

let serverOutput = "";
server.stdout.on("data", (chunk) => {
  serverOutput += chunk;
});
server.stderr.on("data", (chunk) => {
  serverOutput += chunk;
});

async function waitUntilReady() {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    if (server.exitCode !== null) {
      throw new Error(`next start exited early:\n${serverOutput}`);
    }

    try {
      const response = await fetch(`${origin}/es`);
      if (response.ok) return;
    } catch {
      // Server is still starting.
    }

    await new Promise((resolve) => setTimeout(resolve, 200));
  }

  throw new Error(`next start did not become ready:\n${serverOutput}`);
}

async function stopServer() {
  if (server.exitCode !== null) return;

  server.kill("SIGTERM");
  await new Promise((resolve) => {
    const timeout = setTimeout(() => server.kill("SIGKILL"), 5_000);
    server.once("exit", () => {
      clearTimeout(timeout);
      resolve();
    });
  });
}

try {
  await waitUntilReady();

  for (const expectation of [
    {
      locale: "en",
      message: "Page not found",
      cta: "Back to home",
      wrongLocaleMessage: "Página no encontrada",
    },
    {
      locale: "es",
      message: "Página no encontrada",
      cta: "Volver al inicio",
      wrongLocaleMessage: "Page not found",
    },
  ]) {
    const response = await fetch(
      `${origin}/${expectation.locale}/localized-404-runtime-check`,
    );
    const body = (await response.text()).replaceAll("\\", "");

    assert.equal(response.status, 404, `${expectation.locale} status`);
    assert.ok(body.includes(expectation.message), `${expectation.locale} message`);
    assert.ok(body.includes(expectation.cta), `${expectation.locale} CTA`);
    assert.ok(
      body.includes(`"href":"/${expectation.locale}"`),
      `${expectation.locale} home link`,
    );
    assert.ok(
      !body.includes(expectation.wrongLocaleMessage),
      `${expectation.locale} must not render the other locale`,
    );

    console.log(`${expectation.locale}: 404, localized copy, /${expectation.locale} link`);
  }
} finally {
  await stopServer();
}