import React from "react";

export default function HomePage() {
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      minHeight: "100vh",
      justifyContent: "center",
      alignItems: "center",
      padding: "2rem",
      textAlign: "center",
      background: "radial-gradient(circle at top, hsl(210, 30%, 94%), hsl(210, 20%, 98%))"
    }}>
      <div className="card" style={{
        maxWidth: "600px",
        padding: "3rem",
        boxShadow: "0 10px 30px rgba(0, 0, 0, 0.05)"
      }}>
        <h1 style={{ fontSize: "2.5rem", marginBottom: "1rem", fontWeight: "800" }}>
          Retriever Platform
        </h1>
        <p style={{ color: "hsl(215, 15%, 40%)", fontSize: "1.1rem", marginBottom: "2rem" }}>
          The permanent, secure memory layer for enterprise AI applications. 
          Bypass model lock-in and secure corporate knowledge spaces with Row-Level Security.
        </p>
        
        <div style={{ display: "flex", gap: "1rem", justifyContent: "center" }}>
          <a 
            href="http://localhost:8000/docs" 
            target="_blank" 
            rel="noopener noreferrer" 
            style={{
              padding: "0.75rem 1.5rem",
              backgroundColor: "hsl(220, 90%, 50%)",
              color: "white",
              borderRadius: "0.5rem",
              fontWeight: "600",
              boxShadow: "0 4px 12px rgba(37, 99, 235, 0.2)"
            }}
          >
            API Swagger Docs
          </a>
          <a 
            href="http://localhost:8000/health/liveness" 
            target="_blank" 
            rel="noopener noreferrer" 
            style={{
              padding: "0.75rem 1.5rem",
              backgroundColor: "white",
              border: "1px solid hsl(220, 13%, 91%)",
              color: "hsl(224, 71.4%, 4%)",
              borderRadius: "0.5rem",
              fontWeight: "600"
            }}
          >
            Liveness Health
          </a>
        </div>
      </div>
    </div>
  );
}
