"use client";

const Footer = () => {
  return (
    <footer className="fixed bottom-0 left-0 right-0 z-40 border-t border-terminal-border bg-background-secondary px-4 py-3">
      <div className="container mx-auto max-w-6xl">
        <div className="flex flex-wrap justify-center gap-4 text-center font-mono text-sm text-text-muted">
          <span className="text-neon-green">psarc@library:~$</span>
          <span>uv run psarc-library</span>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
