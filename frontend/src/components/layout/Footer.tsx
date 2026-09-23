export function Footer() {
  return (
    <footer className="bg-obsidian border-t border-white/10 py-6">
      <p className="text-center text-sm text-white/55">
        © {new Date().getFullYear()} Ticket Manager — demo application
      </p>
    </footer>
  )
}
