import { render, screen, fireEvent } from "@testing-library/react";
import { usePathname } from "next/navigation";
import React from "react";

import Navigation from "@/components/Navigation";
import { AuthProvider } from "@/contexts/AuthContext";
import { useHealthStatus } from "@/lib/api";

// Mock Next.js Link component
jest.mock("next/link", () => {
  const MockLink = ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  );
  MockLink.displayName = "MockLink";
  return MockLink;
});

// Mock Next.js usePathname hook
jest.mock("next/navigation", () => ({
  usePathname: jest.fn(),
  useRouter: jest.fn(() => ({
    push: jest.fn(),
  })),
}));

// Mock the useHealthStatus hook
jest.mock("../../lib/api", () => ({
  useHealthStatus: jest.fn(),
}));

// Helper function to render components with AuthProvider
const renderWithAuth = (ui: React.ReactElement) => {
  return render(<AuthProvider>{ui}</AuthProvider>);
};

const mockUseHealthStatus = useHealthStatus as jest.MockedFunction<
  typeof useHealthStatus
>;

const mockUsePathname = usePathname as jest.MockedFunction<typeof usePathname>;

describe("Navigation", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseHealthStatus.mockReturnValue("online");
    mockUsePathname.mockReturnValue("/");
    // Mock localStorage
    Storage.prototype.getItem = jest.fn(() => "test-api-key");
  });
  it("renders the PSARC Library logo", () => {
    renderWithAuth(<Navigation />);
    expect(screen.getByText("PSARC Library")).toBeInTheDocument();
  });

  it("renders all navigation items", () => {
    renderWithAuth(<Navigation />);
    // Check that navigation items exist (they appear in both desktop and mobile)
    expect(screen.getAllByText("Songs")).toHaveLength(2);
  });

  it("renders navigation links with correct hrefs", () => {
    renderWithAuth(<Navigation />);
    // Get desktop navigation links - use exact match to exclude logo
    const songsLinks = screen.getAllByRole("link", {
      name: "Songs",
    });
    expect(songsLinks[0]).toHaveAttribute("href", "/songs");
  });

  it("applies active styling to current page", () => {
    mockUsePathname.mockReturnValue("/songs");

    renderWithAuth(<Navigation />);
    const songsLinks = screen.getAllByRole("link", {
      name: "Songs",
    });
    // Both desktop and mobile links should have active styling
    expect(songsLinks[0]).toHaveClass("font-bold", "text-border-accent");
    expect(songsLinks[1]).toHaveClass("font-bold", "text-border-accent");
  });

  describe("Mobile Navigation", () => {
    it("renders mobile menu button", () => {
      renderWithAuth(<Navigation />);
      const menuButton = screen.getByRole("button", {
        name: /Open main menu/,
      });
      expect(menuButton).toBeInTheDocument();
    });

    it("toggles mobile menu when button is clicked", () => {
      renderWithAuth(<Navigation />);
      const menuButton = screen.getByRole("button", {
        name: /Open main menu/,
      });

      // Find all elements with lg:hidden class and get the second one (the mobile menu content)
      const navigation = screen.getByRole("navigation");
      const lgHiddenElements = navigation.querySelectorAll(".lg\\:hidden");
      const mobileMenu = lgHiddenElements[1]; // Second element is the mobile menu content

      expect(mobileMenu).toHaveClass("lg:hidden");
      expect(mobileMenu).toHaveClass("hidden");

      // Click to open menu
      fireEvent.click(menuButton);
      expect(mobileMenu).toHaveClass("lg:hidden");
      expect(mobileMenu).toHaveClass("block");
      expect(mobileMenu).not.toHaveClass("hidden");

      // Click again to close menu
      fireEvent.click(menuButton);
      expect(mobileMenu).toHaveClass("lg:hidden");
      expect(mobileMenu).toHaveClass("hidden");
      expect(mobileMenu).not.toHaveClass("block");
    });

    it("shows hamburger icon when menu is closed", () => {
      renderWithAuth(<Navigation />);
      const hamburgerIcon = screen
        .getByRole("button", { name: /Open main menu/ })
        .querySelector('svg[class*="block"]');
      expect(hamburgerIcon).toBeInTheDocument();
    });

    it("shows close icon when menu is open", () => {
      renderWithAuth(<Navigation />);
      const menuButton = screen.getByRole("button", {
        name: /Open main menu/,
      });

      fireEvent.click(menuButton);

      const closeIcon = screen
        .getByRole("button", { name: /Open main menu/ })
        .querySelector('svg[class*="block"]');
      expect(closeIcon).toBeInTheDocument();
    });

    it("closes mobile menu when navigation link is clicked", () => {
      renderWithAuth(<Navigation />);
      const menuButton = screen.getByRole("button", {
        name: /Open main menu/,
      });

      // Open menu
      fireEvent.click(menuButton);

      // Find the mobile menu content div (second lg:hidden element)
      const navigation = screen.getByRole("navigation");
      const lgHiddenElements = navigation.querySelectorAll(".lg\\:hidden");
      const mobileMenu = lgHiddenElements[1]; // Second element is the mobile menu content

      expect(mobileMenu).toHaveClass("lg:hidden");
      expect(mobileMenu).toHaveClass("block");

      // Click a navigation link in mobile menu
      const songsLinks = screen.getAllByRole("link", {
        name: "Songs",
      });
      const songsLink = songsLinks[1]; // Second one is in mobile menu
      if (songsLink) {
        fireEvent.click(songsLink);
      }

      // Menu should be closed after clicking
      expect(mobileMenu).not.toHaveClass("block");
    });

    it("renders all navigation items in mobile menu", () => {
      renderWithAuth(<Navigation />);
      const menuButton = screen.getByRole("button", {
        name: /Open main menu/,
      });

      fireEvent.click(menuButton);

      // All navigation items should appear twice (desktop and mobile)
      expect(screen.getAllByText("Songs")).toHaveLength(2);
    });

    it("applies active styling to current page in mobile menu", () => {
      mockUsePathname.mockReturnValue("/songs");

      renderWithAuth(<Navigation />);
      const menuButton = screen.getByRole("button", {
        name: /Open main menu/,
      });

      fireEvent.click(menuButton);

      const songsLinks = screen.getAllByRole("link", {
        name: "Songs",
      });
      const mobileSongsLink = songsLinks[1]; // Second one is in mobile menu
      expect(mobileSongsLink).toHaveClass("font-bold", "text-border-accent");
    });
  });

  describe("HealthIndicator integration", () => {
    it("renders HealthIndicator in the navigation", () => {
      mockUseHealthStatus.mockReturnValue("online");

      renderWithAuth(<Navigation />);

      // The HealthIndicator should render a circular indicator
      const indicators = screen
        .getByRole("navigation")
        .querySelectorAll('[title*="Server:"]');
      expect(indicators).toHaveLength(1);
    });

    it("displays online status indicator when server is online", () => {
      mockUseHealthStatus.mockReturnValue("online");

      renderWithAuth(<Navigation />);

      const indicator = screen.getByTitle("Server: ONLINE");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-neon-green");
    });

    it("displays offline status indicator when server is offline", () => {
      mockUseHealthStatus.mockReturnValue("offline");

      renderWithAuth(<Navigation />);

      const indicator = screen.getByTitle("Server: OFFLINE");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-neon-red");
    });

    it("displays checking status indicator when status is being checked", () => {
      mockUseHealthStatus.mockReturnValue("checking");

      renderWithAuth(<Navigation />);

      const indicator = screen.getByTitle("Server: CHECKING");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-yellow-400");
      expect(indicator).toHaveClass("animate-pulse");
    });

    it("positions HealthIndicator next to the logo", () => {
      mockUseHealthStatus.mockReturnValue("online");

      renderWithAuth(<Navigation />);

      // Check that both the logo and health indicator are present
      expect(screen.getByText("PSARC Library")).toBeInTheDocument();
      expect(screen.getByTitle("Server: ONLINE")).toBeInTheDocument();

      // Check that they are both in the navigation
      const nav = screen.getByRole("navigation");
      expect(nav).toContainElement(screen.getByText("PSARC Library"));
      expect(nav).toContainElement(screen.getByTitle("Server: ONLINE"));
    });

    it("includes tooltip with status information", () => {
      mockUseHealthStatus.mockReturnValue("online");

      renderWithAuth(<Navigation />);

      const healthIndicator = screen.getByTitle("Server: ONLINE");
      expect(healthIndicator).toHaveAttribute("title", "Server: ONLINE");
    });

    it("calls useHealthStatus hook when Navigation is rendered", () => {
      mockUseHealthStatus.mockReturnValue("online");

      renderWithAuth(<Navigation />);

      expect(mockUseHealthStatus).toHaveBeenCalledTimes(1);
    });
  });
});
