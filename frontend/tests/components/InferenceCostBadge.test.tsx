import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { InferenceCostBadge } from "@/components/costs/InferenceCostBadge";

describe("InferenceCostBadge", () => {
  it("renders cost in USD format", () => {
    render(<InferenceCostBadge cost={0.0012} />);
    expect(screen.getByText("$0.0012")).toBeInTheDocument();
  });

  it("shows green for low cost", () => {
    const { container } = render(<InferenceCostBadge cost={0.005} />);
    expect(container.firstChild?.textContent).toBe("$0.0050");
  });

  it("renders zero cost", () => {
    render(<InferenceCostBadge cost={0} />);
    expect(screen.getByText("$0.0000")).toBeInTheDocument();
  });
});
