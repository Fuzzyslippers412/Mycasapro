import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ContextStackedBar } from "./ContextStackedBar";

describe("ContextStackedBar", () => {
  it("renders percentages that sum to the context window", () => {
    render(
      <ContextStackedBar
        contextWindow={100}
        reservedOutput={10}
        tokens={{
          system: 20,
          developer: 10,
          memory: 10,
          history: 20,
          retrieval: 10,
          tool_results: 10,
          other: 10,
        }}
      />
    );

    const progress = screen.getByTestId("context-progress");
    const sections = Array.from(progress.querySelectorAll("div"))
      .map((el) => el.style.width)
      .filter((width) => width.endsWith("%"))
      .map((width) => Number(width.replace("%", "")))
      .filter((value) => !Number.isNaN(value));

    const total = sections.reduce((sum, value) => sum + value, 0);
    expect(Math.round(total)).toBe(100);
    expect(screen.getByText(/system · 20/)).toBeInTheDocument();
    expect(screen.getByText(/reserved output · 10/)).toBeInTheDocument();
  });
});
