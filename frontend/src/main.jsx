import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BookOpenCheck,
  CalendarClock,
  Check,
  FlaskConical,
  Plus,
  RefreshCw,
  Search,
  Star,
  Trash2,
  X
} from "lucide-react";

import { api } from "./services/apiClient";
import "./styles/app.css";

const emptyForm = {
  name: "",
  description: "",
  keywordsText: "",
  is_active: true
};

function App() {
  const [fields, setFields] = useState([]);
  const [selectedFieldId, setSelectedFieldId] = useState(null);
  const [papers, setPapers] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [papersLoading, setPapersLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const selectedField = fields.find((field) => field.id === selectedFieldId) || fields[0] || null;

  useEffect(() => {
    loadFields();
  }, []);

  useEffect(() => {
    if (selectedField?.id) {
      setSelectedFieldId(selectedField.id);
      loadPapers(selectedField.id);
    } else {
      setPapers([]);
    }
  }, [selectedField?.id]);

  const generatedQuery = useMemo(() => {
    return parseKeywords(form.keywordsText)
      .map((keyword) => {
        const term = keyword.includes(" ") && !keyword.startsWith('"') ? `"${keyword}"` : keyword;
        return `${term}[Title/Abstract]`;
      })
      .join(" OR ");
  }, [form.keywordsText]);

  async function loadFields() {
    setLoading(true);
    setError("");
    try {
      const data = await api.listResearchFields();
      setFields(data);
      if (!selectedFieldId && data.length) {
        setSelectedFieldId(data[0].id);
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadPapers(fieldId) {
    setPapersLoading(true);
    setError("");
    try {
      setPapers(await api.listPapers(fieldId));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setPapersLoading(false);
    }
  }

  async function handleCreateField(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      const payload = {
        name: form.name,
        description: form.description || null,
        keywords: parseKeywords(form.keywordsText),
        pubmed_query: generatedQuery || null,
        is_active: form.is_active
      };
      const created = await api.createResearchField(payload);
      setForm(emptyForm);
      setSelectedFieldId(created.id);
      await loadFields();
      setNotice("Research field created.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function handleSync() {
    if (!selectedField) return;
    setSyncing(true);
    setError("");
    setNotice("");
    try {
      const result = await api.syncResearchField(selectedField.id);
      await Promise.all([loadFields(), loadPapers(selectedField.id)]);
      setNotice(`Sync complete: ${result.inserted} new papers, ${result.skipped_existing} already tracked.`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSyncing(false);
    }
  }

  async function toggleRead(paper) {
    setError("");
    try {
      const updated = await api.updatePaperStatus(paper.id, !paper.is_read);
      setPapers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      await loadFields();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function deletePaper(paperId) {
    setError("");
    try {
      await api.deletePaper(paperId);
      setPapers((current) => current.filter((paper) => paper.id !== paperId));
      await loadFields();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function deleteField(fieldId) {
    setError("");
    try {
      await api.deleteResearchField(fieldId);
      setSelectedFieldId(null);
      await loadFields();
      setNotice("Research field deleted.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  return (
    <main className="app-shell">
      <section className="sidebar" aria-label="Research field setup">
        <div className="brand">
          <div className="brand-mark">
            <FlaskConical size={24} />
          </div>
          <div>
            <h1>Keep Up Literature</h1>
            <p>Daily PubMed workspaces</p>
          </div>
        </div>

        <form className="field-form" onSubmit={handleCreateField}>
          <div className="section-title">
            <Plus size={18} />
            <h2>Research Fields</h2>
          </div>

          <label>
            Name
            <input
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              placeholder="Cancer immunotherapy"
              required
            />
          </label>

          <label>
            Keywords or contexts
            <textarea
              value={form.keywordsText}
              onChange={(event) => setForm({ ...form, keywordsText: event.target.value })}
              placeholder="single-cell RNA-seq, tumor microenvironment, checkpoint blockade"
              required
            />
          </label>

          <label>
            Description
            <textarea
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
              placeholder="Track recent mechanisms, trials, biomarkers, and translational papers."
            />
          </label>

          <label className="switch-row">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
            />
            Active daily Airflow sync
          </label>

          <div className="query-preview">
            <Search size={16} />
            <span>{generatedQuery || "PubMed query preview appears here."}</span>
          </div>

          <button type="submit" className="primary-button">
            <Plus size={18} />
            Create Workspace
          </button>
        </form>
      </section>

      <section className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">Must-read queue</span>
            <h2>{selectedField?.name || "Create a research field"}</h2>
          </div>
          <button className="sync-button" onClick={handleSync} disabled={!selectedField || syncing}>
            <RefreshCw size={18} className={syncing ? "spin" : ""} />
            {syncing ? "Syncing" : "Sync PubMed"}
          </button>
        </header>

        {(error || notice) && (
          <div className={error ? "message error" : "message notice"}>
            {error || notice}
            <button aria-label="Dismiss message" onClick={() => { setError(""); setNotice(""); }}>
              <X size={16} />
            </button>
          </div>
        )}

        <div className="content-grid">
          <aside className="field-list" aria-label="Research field workspaces">
            {loading ? (
              <div className="empty-state">Loading workspaces...</div>
            ) : fields.length === 0 ? (
              <div className="empty-state">No research fields yet.</div>
            ) : (
              fields.map((field) => (
                <button
                  key={field.id}
                  className={`field-card ${field.id === selectedField?.id ? "selected" : ""}`}
                  onClick={() => setSelectedFieldId(field.id)}
                >
                  <div>
                    <strong>{field.name}</strong>
                    <span>{field.keywords.slice(0, 3).join(", ")}</span>
                  </div>
                  <div className="field-metrics">
                    <span>{field.unread_count} unread</span>
                    <span>{field.paper_count} total</span>
                  </div>
                </button>
              ))
            )}
          </aside>

          <section className="papers-panel">
            {selectedField && (
              <div className="workspace-summary">
                <div>
                  <CalendarClock size={18} />
                  <span>{selectedField.is_active ? "Daily sync active" : "Daily sync paused"}</span>
                </div>
                <code>{selectedField.pubmed_query}</code>
                <button className="icon-button danger" onClick={() => deleteField(selectedField.id)} title="Delete workspace">
                  <Trash2 size={18} />
                </button>
              </div>
            )}

            {papersLoading ? (
              <div className="empty-state tall">Loading papers...</div>
            ) : papers.length === 0 ? (
              <div className="empty-state tall">
                <BookOpenCheck size={36} />
                <h3>No papers saved yet</h3>
                <p>Run a PubMed sync, or wait for Airflow to populate the current month queue.</p>
              </div>
            ) : (
              <PaperTable papers={papers} onToggleRead={toggleRead} onDelete={deletePaper} />
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

function PaperTable({ papers, onToggleRead, onDelete }) {
  return (
    <div className="paper-table-wrap">
      <table className="paper-table">
        <thead>
          <tr>
            <th>Status</th>
            <th>Priority</th>
            <th>Publication</th>
            <th>Journal</th>
            <th>Date</th>
            <th>Authors</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {papers.map((paper) => (
            <tr key={paper.id} className={paper.is_read ? "read-row" : ""}>
              <td>
                <button className={`read-toggle ${paper.is_read ? "read" : ""}`} onClick={() => onToggleRead(paper)}>
                  <Check size={16} />
                  {paper.is_read ? "Read" : "Unread"}
                </button>
              </td>
              <td>
                <div className={`priority-badge ${priorityClass(paper.priority_label)}`}>
                  <Star size={15} />
                  <span>{paper.priority_label}</span>
                  <strong>{Math.round(paper.priority_score)}</strong>
                </div>
                {paper.priority_reasons.length > 0 && (
                  <div className="priority-reasons">
                    {paper.priority_reasons.slice(0, 3).map((reason) => (
                      <span key={reason}>{reason}</span>
                    ))}
                  </div>
                )}
              </td>
              <td className="paper-title">
                <a href={paper.link} target="_blank" rel="noreferrer">{paper.title}</a>
                {paper.abstract && <p>{paper.abstract}</p>}
              </td>
              <td>{paper.journal_name || "Unknown journal"}</td>
              <td>{paper.publication_date || "Unknown"}</td>
              <td>{paper.author_list.slice(0, 5).join(", ")}{paper.author_list.length > 5 ? " et al." : ""}</td>
              <td>
                <button className="icon-button danger" onClick={() => onDelete(paper.id)} title="Delete paper">
                  <Trash2 size={17} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function priorityClass(label) {
  return label.toLowerCase().replace(/\s+/g, "-");
}

function parseKeywords(value) {
  return value
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

createRoot(document.getElementById("root")).render(<App />);
