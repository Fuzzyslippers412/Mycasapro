import { test, expect } from "@playwright/test";

test("agent context settings flow", async ({ page }) => {
  await page.route("**/api/agents", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        agents: [
          {
            id: "agent-1",
            name: "manager",
            model: "gpt",
            provider: "openai",
            context_window_tokens: 32768,
            reserved_output_tokens: 2048,
            budgets: {
              system: 2048,
              memory: 4096,
              history: 8192,
              retrieval: 4096,
              tool_results: 2048,
              safety_margin: 512,
            },
            last_run: {
              status: "ok",
              headroom: 12000,
              component_tokens: {
                system: 1000,
                developer: 300,
                memory: 1200,
                history: 2000,
                retrieval: 1500,
                tool_results: 400,
                other: 200,
              },
              included_summary: {
                history: { token_counts: [400, 400] },
                retrieval: { token_counts: [300, 300], header_tokens: 20 },
                tool_results: { token_counts: [200], header_tokens: 10 },
                user_message: { tokens: 200 },
              },
            },
          },
        ],
      }),
    });
  });

  await page.route("**/api/agents/agent-1/context", async (route) => {
    if (route.request().method() === "PATCH") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "agent-1",
          name: "manager",
          model: "gpt",
          provider: "openai",
          context_window_tokens: 32768,
          reserved_output_tokens: 1024,
          budgets: {
            system: 2048,
            memory: 4096,
            history: 8192,
            retrieval: 4096,
            tool_results: 2048,
            safety_margin: 512,
          },
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        agent: { id: "agent-1", name: "manager", model: "gpt", provider: "openai" },
        budgets: {
          system: 2048,
          memory: 4096,
          history: 8192,
          retrieval: 4096,
          tool_results: 2048,
          safety_margin: 512,
        },
        context_window_tokens: 32768,
        reserved_output_tokens: 2048,
        last_run: {
          status: "ok",
          headroom: 12000,
          component_tokens: {
            system: 1000,
            developer: 300,
            memory: 1200,
            history: 2000,
            retrieval: 1500,
            tool_results: 400,
            other: 200,
          },
          included_summary: {
            history: { token_counts: [400, 400] },
            retrieval: { token_counts: [300, 300], header_tokens: 20 },
            tool_results: { token_counts: [200], header_tokens: 10 },
            user_message: { tokens: 200 },
          },
        },
        runs: [],
      }),
    });
  });

  await page.route("**/api/agents/agent-1/simulate-context", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "ok",
        headroom: 14000,
        trimming_applied: [],
      }),
    });
  });

  await page.goto("/settings");
  await page.getByRole("tab", { name: "Agents" }).click();
  await page.getByRole("tab", { name: "Context" }).click();

  await expect(page.getByText(/Context headroom/)).toBeVisible();

  const reservedInput = page.getByLabel("Reserved output tokens");
  await reservedInput.fill("1024");
  await page.getByRole("button", { name: "Save" }).click();

  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect(page.getByText(/Headroom/)).toBeVisible();
  await expect(page.getByText(/14000 tokens/)).toBeVisible();
});
