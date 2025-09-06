// src/Dashboard.js
import React, { useState } from "react";
import axios from "axios";
import Plot from "react-plotly.js";
import { VegaLite } from "react-vega";

const API_BASE = process.env.REACT_APP_API_URL || "";

export default function Dashboard() {
  const [query, setQuery]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [sql, setSql]             = useState("");
  const [code, setCode]           = useState("");
  const [plotlyData, setPlotlyData] = useState(null);
  const [error, setError]         = useState("");
  const [vegaSpec, setVegaSpec]   = useState(null);
  const [vegaData, setVegaData]   = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSql("");
    setCode("");
    setPlotlyData(null);
    setVegaSpec(null);
    setVegaData(null);

    try {
      const resp = await axios.post(
        `${API_BASE}/interactive/`,
        { nl: query }
      );

      setSql(resp.data.sql || "");
      setCode(resp.data.code || "");

      if (resp.data.plotly_json) {
        const parsed = JSON.parse(resp.data.plotly_json);
        setPlotlyData(parsed);
      }

      if (resp.data.spec && resp.data.data) {
        setVegaSpec(resp.data.spec);
        setVegaData(resp.data.data);
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    }

    setLoading(false);
  };

  return (
    <div className="p-4">
      <h1 className="text-2xl mb-4">Football Dashboard</h1>

      <form onSubmit={handleSubmit} className="mb-4 flex">
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Ask me e.g. Top 5 goal scorers"
          className="p-2 border rounded flex-grow"
        />
        <button
          type="submit"
          disabled={loading}
          className="ml-2 p-2 bg-blue-600 text-white rounded"
        >
          {loading ? "Loading…" : "Go"}
        </button>
      </form>

      {error && <div className="text-red-600 mb-4">{error}</div>}

      {sql && (
        <div className="mb-4">
          <strong>SQL:</strong> <code className="bg-gray-100 p-1 rounded">{sql}</code>
        </div>
      )}

      {vegaSpec && vegaData && (
        <div className="border p-4 mb-4">
          <VegaLite spec={vegaSpec} data={{ table: vegaData }} />
        </div>
      )}

      {plotlyData && (
        <div className="border p-4 mb-4">
          <Plot
            data={plotlyData.data}
            layout={{ ...plotlyData.layout, autosize: true }}
            style={{ width: "100%" }}
          />
        </div>
      )}

      {code && (
        <details className="mb-4">
          <summary className="cursor-pointer text-blue-600">View Python code</summary>
          <pre className="bg-gray-100 p-4 overflow-auto">{code}</pre>
        </details>
      )}
    </div>
);
}
