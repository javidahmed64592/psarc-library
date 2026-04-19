import { render, screen } from "@testing-library/react";

import Footer from "@/components/Footer";

// Mock the API
jest.mock("../../lib/api", () => ({
  getConfig: jest.fn(),
}));

describe("Footer", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the footer component", () => {
    render(<Footer />);

    const footer = screen.getByRole("contentinfo");
    expect(footer).toBeInTheDocument();
  });

  it("displays the terminal prompt", () => {
    render(<Footer />);

    expect(screen.getByText("psarc@library:~$")).toBeInTheDocument();
  });

  it("has fixed positioning at the bottom", () => {
    render(<Footer />);

    const footer = screen.getByRole("contentinfo");
    expect(footer).toHaveClass("fixed", "bottom-0", "left-0", "right-0");
  });

  it("has proper z-index for overlay", () => {
    render(<Footer />);

    const footer = screen.getByRole("contentinfo");
    expect(footer).toHaveClass("z-40");
  });

  it("has terminal styling", () => {
    render(<Footer />);

    const footer = screen.getByRole("contentinfo");
    expect(footer).toHaveClass(
      "bg-background-secondary",
      "border-t",
      "border-terminal-border"
    );
  });

  it("has responsive layout with flexbox", () => {
    render(<Footer />);

    const contentDiv = screen.getByText("psarc@library:~$").closest("div");
    expect(contentDiv).toHaveClass(
      "text-center",
      "flex",
      "flex-wrap",
      "justify-center",
      "gap-4"
    );
  });

  it("has monospace font styling", () => {
    render(<Footer />);

    const contentDiv = screen.getByText("psarc@library:~$").closest("div");
    expect(contentDiv).toHaveClass("font-mono", "text-sm");
  });

  it("has neon green color for terminal prompt", () => {
    render(<Footer />);

    const terminalPrompt = screen.getByText("psarc@library:~$");
    expect(terminalPrompt).toHaveClass("text-neon-green");
  });

  it("has proper container constraints", () => {
    render(<Footer />);

    const container = screen
      .getByRole("contentinfo")
      .querySelector(".container");
    expect(container).toHaveClass("mx-auto", "max-w-6xl");
  });

  it("renders with semantic footer element", () => {
    render(<Footer />);

    const footer = screen.getByRole("contentinfo");
    expect(footer.tagName).toBe("FOOTER");
  });
});
