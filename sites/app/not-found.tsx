export default function NotFound() {
  return (
    <main
      style={{
        minHeight: "60vh",
        display: "grid",
        placeItems: "center",
        fontFamily: "system-ui, sans-serif",
        color: "#444",
        padding: "2rem",
        textAlign: "center",
      }}
    >
      <div>
        <h1 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>Site not found</h1>
        <p style={{ color: "#888" }}>This preview link isn&rsquo;t active.</p>
      </div>
    </main>
  )
}
