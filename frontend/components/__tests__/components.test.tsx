import * as React from "react";
import { describe, test, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import EngagementBadge from "../EngagementBadge";
import ChurnRiskBar from "../ChurnRiskBar";

describe("EngagementBadge Component Boundary Values", () => {
  test("Engagement score 39 (boundary for Low)", () => {
    render(<EngagementBadge score={39} />);
    const badge = screen.getByText(/39/i);
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("39 (Low)");
    // Should have destructive (red) styling
    expect(badge.className).toContain("bg-red-500");
  });

  test("Engagement score 40 (boundary for Medium)", () => {
    render(<EngagementBadge score={40} />);
    const badge = screen.getByText(/40/i);
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("40 (Medium)");
    // Should have warning (yellow) styling
    expect(badge.className).toContain("bg-amber-500");
  });

  test("Engagement score 69 (boundary for Medium)", () => {
    render(<EngagementBadge score={69} />);
    const badge = screen.getByText(/69/i);
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("69 (Medium)");
    // Should have warning (yellow) styling
    expect(badge.className).toContain("bg-amber-500");
  });

  test("Engagement score 70 (boundary for High)", () => {
    render(<EngagementBadge score={70} />);
    const badge = screen.getByText(/70/i);
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("70 (High)");
    // Should have success (green) styling
    expect(badge.className).toContain("bg-emerald-500");
  });
});

describe("ChurnRiskBar Component Boundary Values", () => {
  test("Churn risk 0.39 (39% width fill)", () => {
    const { container } = render(<ChurnRiskBar risk={0.39} />);
    expect(screen.getByText("39%")).toBeInTheDocument();
    const fillBar = container.querySelector(".bg-red-500") as HTMLElement;
    expect(fillBar).toBeInTheDocument();
    expect(fillBar.style.width).toBe("39%");
  });

  test("Churn risk 0.40 (40% width fill)", () => {
    const { container } = render(<ChurnRiskBar risk={0.40} />);
    expect(screen.getByText("40%")).toBeInTheDocument();
    const fillBar = container.querySelector(".bg-red-500") as HTMLElement;
    expect(fillBar).toBeInTheDocument();
    expect(fillBar.style.width).toBe("40%");
  });

  test("Churn risk 0.69 (69% width fill)", () => {
    const { container } = render(<ChurnRiskBar risk={0.69} />);
    expect(screen.getByText("69%")).toBeInTheDocument();
    const fillBar = container.querySelector(".bg-red-500") as HTMLElement;
    expect(fillBar).toBeInTheDocument();
    expect(fillBar.style.width).toBe("69%");
  });

  test("Churn risk 0.70 (70% width fill)", () => {
    const { container } = render(<ChurnRiskBar risk={0.70} />);
    expect(screen.getByText("70%")).toBeInTheDocument();
    const fillBar = container.querySelector(".bg-red-500") as HTMLElement;
    expect(fillBar).toBeInTheDocument();
    expect(fillBar.style.width).toBe("70%");
  });
});
