import React, { useDeferredValue, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Archive,
  BookOpenCheck,
  CalendarClock,
  Check,
  Download,
  FlaskConical,
  PauseCircle,
  PlayCircle,
  Plus,
  RefreshCw,
  Search,
  Star,
  StickyNote,
  Trash2,
  X
} from "lucide-react";

import { api } from "./services/apiClient";
import "./styles/app.css";

const emptyForm = { name: "", description: "", keywordsText: "", is_active: true };
const defaultFilters = { status: "queue", starred: false, search: "" };

function App() {
  const [fields, setFields] = useState([]);
  const [selectedFieldId, setSelectedFieldId] = usePersistentState("kul.selected-field", null);
  const [papers, setPapers] = useState([]);
  const [form, setForm] = usePersistentState("kul.workspace-draft", emptyForm);
  const [filters, setFilters] = usePersistentState("kul.paper-filters", defaultFilters);
  const [loading, setLoading] = useState(true);
  const [papersLoading, setPapersLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const deferredSearch = useDeferredValue(filters.search);

  const selectedField = fields.find((field) => field.id === selectedFieldId) || fields[0] || null;
  const keywords = useMemo(() => parseKeywords(form.keywordsText), [form.keywordsText]);

  useEffect(() => {
    loadFields();
  }, []);

  useEffect(() => {
    if (!selectedField?.id) {
      setPapers([]);
      return;
    }
    if (selectedField.id !== selectedFieldId) setSelectedFieldId(selectedField.id);
    loadPapers(selectedField.id);
  }, [selectedField?.id, filters.status, filters.starred, deferredSearch]);

  async function loadFields() {
    setLoading(true);
    try {
      const data = await api.listResearchFields();
      setFields(data);
      if (data.length && !data.some((field) => field.id === selectedFieldId)) {
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
    try {
      const data = await api.listPapers(fieldId, {
        status: filters.status,
        starred: filters.starred,
        search: deferredSearch
      });
      setPapers(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setPapersLoading(false);
    }
  }

  async function handleCreateField(event) {
    event.preventDefault();
    clearMessages();
    try {
      const created = await api.createResearchField({
        name: form.name.trim(),
        description: form.description.trim() || null,
        keywords,
        is_active: form.is_active
      });
      setForm(emptyForm);
      setSelectedFieldId(created.id);
      await loadFields();
      setNotice("Workspace created. Its first sync will collect the recent literature backlog.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function handleSync() {
    if (!selectedField) return;
    setSyncing(true);
    clearMessages();
    try {
      const result = await api.syncResearchField(selectedField.id);
      await Promise.all([loadFields(), loadPapers(selectedField.id)]);
      const range = result.sync_from && result.sync_to ? ` (${result.sync_from} to ${result.sync_to})` : "";
      setNotice(
        `Sync complete${range}: ${result.inserted} new, ${result.skipped_existing} already tracked, ` +
          `${result.skipped_irrelevant} off-topic, ${result.skipped_deleted} previously removed.`
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSyncing(false);
    }
  }

  async function updatePaper(paper, changes) {
    setError("");
    try {
      await api.updatePaper(paper.id, changes);
      await Promise.all([loadFields(), loadPapers(selectedField.id)]);
      return true;
    } catch (requestError) {
      setError(requestError.message);
      return false;
    }
  }

  async function deletePaper(paper) {
    if (!window.confirm(`Remove “${paper.title}” from this workspace? It will not be re-imported.`)) return;
    setError("");
    try {
      await api.deletePaper(paper.id);
      await Promise.all([loadFields(), loadPapers(selectedField.id)]);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function toggleWorkspace() {
    if (!selectedField) return;
    clearMessages();
    try {
      await api.updateResearchField(selectedField.id, { is_active: !selectedField.is_active });
      await loadFields();
      setNotice(selectedField.is_active ? "Automatic sync paused." : "Automatic sync enabled.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function deleteField(field) {
    if (!window.confirm(`Delete “${field.name}” and all of its saved papers and notes?`)) return;
    clearMessages();
    try {
      await api.deleteResearchField(field.id);
      setSelectedFieldId(null);
      await loadFields();
      setNotice("Workspace deleted.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function clearMessages() {
    setError("");
    setNotice("");
  }

  return (
    <main className="app-shell">
      <section className="sidebar" aria-label="Research field setup">
        <div className="brand">
          <div className="brand-mark"><FlaskConical size={24} /></div>
          <div>
            <h1>Keep Up Literature</h1>
            <p>A durable research reading queue</p>
          </div>
        </div>

        <form className="field-form" onSubmit={handleCreateField}>
          <div className="section-title"><Plus size={18} /><h2>New workspace</h2></div>
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
              placeholder="Mechanisms, trials, biomarkers, and translational studies."
            />
          </label>
          <label className="switch-row">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
            />
            Keep this workspace automatically synced
          </label>
          <div className="query-preview">
            <Search size={16} />
            <span>{keywords.length ? `${keywords.length} focused term${keywords.length === 1 ? "" : "s"}: ${keywords.join(", ")}` : "Add terms to build a focused PubMed query."}</span>
          </div>
          <button type="submit" className="primary-button" disabled={!form.name.trim() || keywords.length === 0}>
            <Plus size={18} /> Create Workspace
          </button>
          <p className="draft-hint">This draft is saved in your browser until you create the workspace.</p>
        </form>
      </section>

      <section className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">Literature workspace</span>
            <h2>{selectedField?.name || "Create a research field"}</h2>
          </div>
          <button className="sync-button" onClick={handleSync} disabled={!selectedField || syncing}>
            <RefreshCw size={18} className={syncing ? "spin" : ""} />
            {syncing ? "Catching up…" : "Sync PubMed"}
          </button>
        </header>

        {(error || notice) && (
          <div className={error ? "message error" : "message notice"} role="status">
            {error || notice}
            <button aria-label="Dismiss message" onClick={clearMessages}><X size={16} /></button>
          </div>
        )}

        <div className="content-grid">
          <aside className="field-list" aria-label="Research workspaces">
            {loading ? (
              <div className="empty-state">Loading workspaces…</div>
            ) : fields.length === 0 ? (
              <div className="empty-state">No research fields yet.</div>
            ) : fields.map((field) => (
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
                  <span>{field.paper_count} in queue</span>
                  <span className={field.is_active ? "active" : "paused"}>{field.is_active ? "auto" : "paused"}</span>
                </div>
              </button>
            ))}
          </aside>

          <section className="papers-panel">
            {selectedField && (
              <>
                <div className="workspace-summary">
                  <div>
                    <CalendarClock size={18} />
                    <span>
                      {selectedField.last_sync_status === "error"
                        ? "Last sync failed"
                        : selectedField.last_synced_at
                          ? `Synced ${formatDateTime(selectedField.last_synced_at)}`
                          : "Ready for first 30-day sync"}
                    </span>
                  </div>
                  <code title={selectedField.pubmed_query}>{selectedField.pubmed_query}</code>
                  <div className="workspace-actions">
                    <button className="icon-button neutral" onClick={toggleWorkspace} title={selectedField.is_active ? "Pause automatic sync" : "Enable automatic sync"}>
                      {selectedField.is_active ? <PauseCircle size={18} /> : <PlayCircle size={18} />}
                    </button>
                    <button className="icon-button danger" onClick={() => deleteField(selectedField)} title="Delete workspace"><Trash2 size={18} /></button>
                  </div>
                </div>
                {selectedField.last_sync_error && <div className="sync-error">{selectedField.last_sync_error}</div>}

                <PaperControls
                  filters={filters}
                  onChange={setFilters}
                  count={papers.length}
                  onExport={() => exportCsv(selectedField, papers)}
                />
              </>
            )}

            {papersLoading ? (
              <div className="empty-state tall">Loading papers…</div>
            ) : papers.length === 0 ? (
              <div className="empty-state tall">
                <BookOpenCheck size={36} />
                <h3>{filters.search || filters.starred || filters.status !== "queue" ? "No papers match these filters" : "Your queue is clear"}</h3>
                <p>Sync PubMed to catch up from the last successful run. Your queue, stars, notes, and reading state are saved automatically.</p>
              </div>
            ) : (
              <PaperTable papers={papers} onUpdate={updatePaper} onDelete={deletePaper} />
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

function PaperControls({ filters, onChange, count, onExport }) {
  const statuses = [
    ["queue", "Queue"], ["unread", "Unread"], ["read", "Read"], ["archived", "Archive"], ["all", "All"]
  ];
  return (
    <div className="paper-controls">
      <div className="status-tabs" aria-label="Paper status filter">
        {statuses.map(([value, label]) => (
          <button key={value} className={filters.status === value ? "selected" : ""} onClick={() => onChange({ ...filters, status: value })}>{label}</button>
        ))}
      </div>
      <label className="search-control">
        <Search size={16} />
        <input value={filters.search} onChange={(event) => onChange({ ...filters, search: event.target.value })} placeholder="Search titles, abstracts, journals, or notes" />
      </label>
      <button className={`filter-button ${filters.starred ? "selected" : ""}`} onClick={() => onChange({ ...filters, starred: !filters.starred })}>
        <Star size={16} fill={filters.starred ? "currentColor" : "none"} /> Starred
      </button>
      <button className="filter-button" onClick={onExport} disabled={count === 0}><Download size={16} /> CSV</button>
      <span className="result-count">{count} shown</span>
    </div>
  );
}

function PaperTable({ papers, onUpdate, onDelete }) {
  return (
    <div className="paper-table-wrap">
      <table className="paper-table">
        <thead><tr><th>Keep</th><th>Status</th><th>Priority</th><th>Publication</th><th>Journal / date</th><th>Actions</th></tr></thead>
        <tbody>
          {papers.map((paper) => <PaperRow key={paper.id} paper={paper} onUpdate={onUpdate} onDelete={onDelete} />)}
        </tbody>
      </table>
    </div>
  );
}

function PaperRow({ paper, onUpdate, onDelete }) {
  const [notesOpen, setNotesOpen] = useState(false);
  const [notes, setNotes] = useState(paper.notes || "");
  const [savingNotes, setSavingNotes] = useState(false);

  useEffect(() => setNotes(paper.notes || ""), [paper.notes]);

  async function saveNotes() {
    setSavingNotes(true);
    try {
      const saved = await onUpdate(paper, { notes: notes.trim() || null });
      if (saved) setNotesOpen(false);
    } finally {
      setSavingNotes(false);
    }
  }

  return (
    <>
      <tr className={`${paper.is_read ? "read-row" : ""} ${paper.is_archived ? "archived-row" : ""}`}>
        <td>
          <button className={`star-button ${paper.is_starred ? "selected" : ""}`} onClick={() => onUpdate(paper, { is_starred: !paper.is_starred })} title={paper.is_starred ? "Remove star" : "Star paper"}>
            <Star size={19} fill={paper.is_starred ? "currentColor" : "none"} />
          </button>
        </td>
        <td>
          <button className={`read-toggle ${paper.is_read ? "read" : ""}`} onClick={() => onUpdate(paper, { is_read: !paper.is_read })}>
            <Check size={16} /> {paper.is_read ? "Read" : "Unread"}
          </button>
        </td>
        <td>
          <div className={`priority-badge ${priorityClass(paper.priority_label)}`}><Star size={15} /><span>{paper.priority_label}</span><strong>{Math.round(paper.priority_score)}</strong></div>
          {paper.priority_reasons.length > 0 && <div className="priority-reasons">{paper.priority_reasons.slice(0, 3).map((reason) => <span key={reason}>{reason}</span>)}</div>}
        </td>
        <td className="paper-title">
          <a href={paper.link} target="_blank" rel="noreferrer">{paper.title}</a>
          {paper.abstract && <p>{paper.abstract}</p>}
          <small>{formatAuthors(paper.author_list)}</small>
        </td>
        <td><strong>{paper.journal_name || "Unknown journal"}</strong><span className="paper-date">{paper.publication_date || "Unknown date"}</span></td>
        <td>
          <div className="row-actions">
            <button className={`icon-button neutral ${paper.notes ? "has-note" : ""}`} onClick={() => setNotesOpen(!notesOpen)} title="Research notes"><StickyNote size={17} /></button>
            <button className="icon-button neutral" onClick={() => onUpdate(paper, { is_archived: !paper.is_archived })} title={paper.is_archived ? "Return to queue" : "Archive"}><Archive size={17} /></button>
            <button className="icon-button danger" onClick={() => onDelete(paper)} title="Remove permanently"><Trash2 size={17} /></button>
          </div>
        </td>
      </tr>
      {notesOpen && (
        <tr className="notes-row"><td colSpan="6">
          <div className="notes-editor">
            <div><strong>Research notes</strong><span>Saved permanently with this paper.</span></div>
            <textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Key result, caveats, follow-up experiments, or why this matters…" />
            <div className="notes-actions"><button onClick={() => setNotesOpen(false)}>Cancel</button><button className="primary-button compact" onClick={saveNotes} disabled={savingNotes}>{savingNotes ? "Saving…" : "Save notes"}</button></div>
          </div>
        </td></tr>
      )}
    </>
  );
}

function usePersistentState(key, initialValue) {
  const [value, setValue] = useState(() => {
    try {
      const saved = window.localStorage.getItem(key);
      return saved === null ? initialValue : JSON.parse(saved);
    } catch {
      return initialValue;
    }
  });
  useEffect(() => {
    try { window.localStorage.setItem(key, JSON.stringify(value)); } catch { /* Storage can be disabled. */ }
  }, [key, value]);
  return [value, setValue];
}

function exportCsv(field, papers) {
  const columns = ["pubmed_id", "title", "journal", "publication_date", "authors", "priority", "read", "starred", "archived", "notes", "link"];
  const rows = papers.map((paper) => [paper.pubmed_id, paper.title, paper.journal_name, paper.publication_date, paper.author_list.join("; "), paper.priority_score, paper.is_read, paper.is_starred, paper.is_archived, paper.notes, paper.link]);
  const csv = [columns, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${field.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "literature"}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function csvCell(value) {
  const text = value == null ? "" : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

function parseKeywords(value) {
  return Array.from(new Set(value.split(/[,\n]/).map((item) => item.trim()).filter(Boolean)));
}

function priorityClass(label) {
  return label.toLowerCase().replace(/\s+/g, "-");
}

function formatAuthors(authors) {
  if (!authors?.length) return "Authors unavailable";
  return `${authors.slice(0, 5).join(", ")}${authors.length > 5 ? " et al." : ""}`;
}

function formatDateTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

createRoot(document.getElementById("root")).render(<App />);
