import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, Edit2, ChevronDown, ChevronUp, X, Tag, Settings, Users, RotateCcw } from 'lucide-react';

const API_BASE = process.env.REACT_APP_API_URL || 'https://api-timesheet.firsteconomy.com';

const authHeaders = () => ({
  'Authorization': `Bearer ${localStorage.getItem('token')}`,
  'Content-Type': 'application/json',
});

// ─── Current month in YYYY-MM format ────────────────────────────────────────
function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

// ─── Keyword chip component ──────────────────────────────────────────────────
function KeywordChip({ label, onRemove }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '4px',
      background: '#eef2ff', color: '#4338ca',
      padding: '2px 8px', borderRadius: '12px', fontSize: '12px', fontWeight: 500,
    }}>
      {label}
      {onRemove && (
        <X
          size={10}
          style={{ cursor: 'pointer', opacity: 0.7 }}
          onClick={() => onRemove(label)}
        />
      )}
    </span>
  );
}

// ─── Keyword tag input ───────────────────────────────────────────────────────
function KeywordInput({ tags, onChange }) {
  const [inputVal, setInputVal] = useState('');

  const addTag = (val) => {
    const v = val.trim().toLowerCase();
    if (v && !tags.includes(v)) onChange([...tags, v]);
    setInputVal('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addTag(inputVal);
    } else if (e.key === 'Backspace' && !inputVal && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  };

  const removeTag = (tag) => onChange(tags.filter(t => t !== tag));

  return (
    <div style={{
      border: '1px solid #d1d5db', borderRadius: '6px', padding: '6px 8px',
      display: 'flex', flexWrap: 'wrap', gap: '4px', minHeight: '38px',
      background: '#fff', cursor: 'text',
    }}
    onClick={() => document.getElementById('kw-input')?.focus()}
    >
      {tags.map(t => <KeywordChip key={t} label={t} onRemove={removeTag} />)}
      <input
        id="kw-input"
        value={inputVal}
        onChange={e => setInputVal(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => { if (inputVal.trim()) addTag(inputVal); }}
        placeholder={tags.length === 0 ? 'Type keyword and press Enter…' : ''}
        style={{
          border: 'none', outline: 'none', fontSize: '13px',
          flex: 1, minWidth: '120px', background: 'transparent',
        }}
      />
    </div>
  );
}

// ─── Add / Edit modal ────────────────────────────────────────────────────────
function ProjectModal({ mode, project, onClose, onSave }) {
  const [name, setName] = useState(project?.name || '');
  const [description, setDescription] = useState(project?.description || '');
  const [keywords, setKeywords] = useState(project?.keywords || []);
  const [cost, setCost] = useState(project?.total_cost != null ? String(project.total_cost) : '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!name.trim()) { setError('Project name is required'); return; }
    const parsedCost = cost !== '' ? parseFloat(cost) : 0;
    if (cost !== '' && isNaN(parsedCost)) { setError('Project cost must be a valid number'); return; }
    setSaving(true);
    setError('');
    try {
      await onSave({ name: name.trim(), description: description.trim(), keywords, total_cost: parsedCost });
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save project');
    } finally {
      setSaving(false);
    }
  };

  const overlayStyle = {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000,
  };
  const boxStyle = {
    background: '#fff', borderRadius: '12px', padding: '28px',
    width: '480px', maxWidth: '90vw', boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
  };

  return (
    <div style={overlayStyle} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={boxStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: '#111' }}>
            {mode === 'add' ? 'Add Project' : 'Edit Project'}
          </h3>
          <X size={20} style={{ cursor: 'pointer', color: '#6b7280' }} onClick={onClose} />
        </div>

        <label style={{ fontSize: '13px', fontWeight: 500, color: '#374151', display: 'block', marginBottom: '4px' }}>
          Project Name *
        </label>
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="e.g. Mahindra Manulife"
          autoFocus={mode === 'add'}
          style={{
            width: '100%', boxSizing: 'border-box', padding: '8px 10px',
            border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '14px',
            marginBottom: '16px', outline: 'none',
          }}
        />
        <label style={{ fontSize: '13px', fontWeight: 500, color: '#374151', display: 'block', marginBottom: '4px' }}>
          Description
        </label>
        <input
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Optional project description"
          style={{
            width: '100%', boxSizing: 'border-box', padding: '8px 10px',
            border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '14px',
            marginBottom: '16px', outline: 'none',
          }}
        />
        <label style={{ fontSize: '13px', fontWeight: 500, color: '#374151', display: 'block', marginBottom: '4px' }}>
          Project Cost (₹)
        </label>
        <input
          type="number"
          min="0"
          step="0.01"
          value={cost}
          onChange={e => setCost(e.target.value)}
          placeholder="e.g. 500000"
          style={{
            width: '100%', boxSizing: 'border-box', padding: '8px 10px',
            border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '14px',
            marginBottom: '16px', outline: 'none',
          }}
        />

        <label style={{ fontSize: '13px', fontWeight: 500, color: '#374151', display: 'block', marginBottom: '4px' }}>
          Keywords
        </label>
        <p style={{ fontSize: '12px', color: '#6b7280', margin: '0 0 8px' }}>
          Activity records whose project name contains any keyword will be matched to this project.
          Press Enter or comma to add each keyword.
        </p>
        <KeywordInput tags={keywords} onChange={setKeywords} />

        {error && <p style={{ color: '#ef4444', fontSize: '13px', marginTop: '8px' }}>{error}</p>}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px', border: '1px solid #d1d5db', borderRadius: '6px',
              background: '#fff', cursor: 'pointer', fontSize: '14px', color: '#374151',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            style={{
              padding: '8px 20px', border: 'none', borderRadius: '6px',
              background: saving ? '#a5b4fc' : '#667eea', color: '#fff',
              cursor: saving ? 'default' : 'pointer', fontSize: '14px', fontWeight: 500,
            }}
          >
            {saving ? 'Saving…' : mode === 'add' ? 'Create Project' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Developer breakdown row ─────────────────────────────────────────────────
function DevBreakdown({ projectId, month }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch(`${API_BASE}/api/admin/projects/${projectId}/developers?month=${month}`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError('Failed to load'); setLoading(false); } });
    return () => { cancelled = true; };
  }, [projectId, month]);

  const cellStyle = { padding: '8px 12px', fontSize: '13px', color: '#374151' };
  const headerCellStyle = { ...cellStyle, fontWeight: 600, color: '#6b7280', fontSize: '11px', textTransform: 'uppercase' };

  if (loading) return (
    <td colSpan={6} style={{ padding: '16px', textAlign: 'center', color: '#9ca3af', fontSize: '13px' }}>
      Loading developer breakdown…
    </td>
  );
  if (error) return (
    <td colSpan={6} style={{ padding: '16px', textAlign: 'center', color: '#ef4444', fontSize: '13px' }}>{error}</td>
  );
  if (!data?.developers?.length) return (
    <td colSpan={6} style={{ padding: '16px', textAlign: 'center', color: '#9ca3af', fontSize: '13px' }}>
      No activity found for this project in {month}.
    </td>
  );

  return (
    <td colSpan={6} style={{ padding: '0 0 0 48px', background: '#f9fafb' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
            <th style={{ ...headerCellStyle, textAlign: 'left' }}>Developer</th>
            <th style={{ ...headerCellStyle, textAlign: 'right' }}>Hours ({month})</th>
            <th style={{ ...headerCellStyle, textAlign: 'left' }}>Raw project names matched</th>
          </tr>
        </thead>
        <tbody>
          {data.developers.map(dev => (
            <tr key={dev.developer_id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={cellStyle}>
                <div style={{ fontWeight: 500 }}>{dev.developer_name}</div>
                <div style={{ fontSize: '11px', color: '#9ca3af' }}>{dev.developer_id}</div>
              </td>
              <td style={{ ...cellStyle, textAlign: 'right', fontWeight: 600, color: '#667eea' }}>
                {dev.total_hours}h
              </td>
              <td style={cellStyle}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {dev.matched_project_names.map(n => (
                    <span key={n} style={{
                      background: '#f3f4f6', color: '#6b7280',
                      padding: '1px 6px', borderRadius: '4px', fontSize: '11px',
                    }}>{n}</span>
                  ))}
                </div>
              </td>
            </tr>
          ))}
          <tr>
            <td style={{ ...cellStyle, fontWeight: 600 }}>Total</td>
            <td style={{ ...cellStyle, textAlign: 'right', fontWeight: 700, color: '#667eea' }}>
              {data.total_hours}h
            </td>
            <td />
          </tr>
        </tbody>
      </table>
    </td>
  );
}

// ─── Main AdminPage ──────────────────────────────────────────────────────────
export default function AdminPage() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState(currentMonth());
  const [expandedId, setExpandedId] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingProject, setEditingProject] = useState(null);   // { id, name, keywords }
  const [deletingId, setDeletingId] = useState(null);
  const [deleteConfirmName, setDeleteConfirmName] = useState('');

  const loadProjects = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/projects`, { headers: authHeaders() });
      const data = await res.json();
      setProjects(data.projects || []);
    } catch {
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadProjects(); }, [loadProjects]);

  const handleCreate = async ({ name, description, keywords, total_cost }) => {
    const res = await fetch(`${API_BASE}/api/admin/projects`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ name, description, keywords, total_cost }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to create');
    }
    await loadProjects();
  };

  const handleUpdate = async ({ name, description, keywords, total_cost }) => {
    const res = await fetch(`${API_BASE}/api/admin/projects/${editingProject.id}`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({ name, description, keywords, total_cost }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to update project');
    }
    await loadProjects();
  };

  const handleDelete = async (id) => {
    await fetch(`${API_BASE}/api/admin/projects/${id}`, { method: 'DELETE', headers: authHeaders() });
    setDeletingId(null);
    setDeleteConfirmName('');
    if (expandedId === id) setExpandedId(null);
    await loadProjects();
  };

  const handleReactivate = async (id) => {
    await fetch(`${API_BASE}/api/admin/projects/${id}/reactivate`, { method: 'PUT', headers: authHeaders() });
    await loadProjects();
  };

  // ── Styles ──────────────────────────────────────────────────────────────────
  const pageStyle = {
    maxWidth: '1200px', margin: '0 auto', padding: '32px 20px',
  };
  const headerRowStyle = {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px',
  };
  const titleStyle = {
    display: 'flex', alignItems: 'center', gap: '10px',
    fontSize: '22px', fontWeight: 700, color: '#111',
  };
  const addBtnStyle = {
    display: 'flex', alignItems: 'center', gap: '6px',
    padding: '9px 16px', background: '#667eea', color: '#fff',
    border: 'none', borderRadius: '8px', cursor: 'pointer',
    fontSize: '14px', fontWeight: 500,
  };
  const tableWrapStyle = {
    background: '#fff', borderRadius: '12px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.08)', overflow: 'hidden',
  };
  const thStyle = {
    padding: '12px 16px', textAlign: 'left', fontSize: '11px',
    fontWeight: 600, color: '#6b7280', textTransform: 'uppercase',
    background: '#f9fafb', borderBottom: '1px solid #e5e7eb',
  };
  const tdStyle = {
    padding: '12px 16px', fontSize: '14px', color: '#374151',
    borderBottom: '1px solid #f3f4f6', verticalAlign: 'middle',
  };
  const iconBtnStyle = (color) => ({
    display: 'inline-flex', alignItems: 'center', gap: '4px',
    padding: '5px 10px', border: `1px solid ${color}20`,
    borderRadius: '6px', background: `${color}10`, color,
    cursor: 'pointer', fontSize: '12px', fontWeight: 500,
  });

  return (
    <div style={pageStyle}>
      {/* Header */}
      <div style={headerRowStyle}>
        <div style={titleStyle}>
          <Settings size={22} color="#667eea" />
          Project Management
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#6b7280' }}>
            <span>Month:</span>
            <input
              type="month"
              value={selectedMonth}
              onChange={e => { setSelectedMonth(e.target.value); setExpandedId(null); }}
              style={{
                padding: '5px 8px', border: '1px solid #d1d5db', borderRadius: '6px',
                fontSize: '13px', outline: 'none', color: '#374151',
              }}
            />
          </div>
          <button style={addBtnStyle} onClick={() => setShowAddModal(true)}>
            <Plus size={16} />
            Add Project
          </button>
        </div>
      </div>

      {/* Projects table */}
      <div style={tableWrapStyle}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>Loading projects…</div>
        ) : projects.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>
            No projects yet. Click "Add Project" to create one.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={thStyle}>Project Name</th>
                <th style={thStyle}>Keywords</th>
                <th style={thStyle}>Cost (₹)</th>
                <th style={thStyle}>Status</th>
                <th style={thStyle}>Actions</th>
                <th style={{ ...thStyle, width: '40px' }}></th>
              </tr>
            </thead>
            <tbody>
              {projects.map(proj => (
                <React.Fragment key={proj.id}>
                  {/* Main row */}
                  <tr style={{ background: expandedId === proj.id ? '#f0f4ff' : '#fff' }}>
                    <td style={tdStyle}>
                      <div style={{ fontWeight: 600 }}>{proj.name}</div>
                      {proj.description && (
                        <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '2px' }}>
                          {proj.description}
                        </div>
                      )}
                    </td>
                    <td style={tdStyle}>
                      {proj.keywords.length > 0 ? (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                          {proj.keywords.map(k => <KeywordChip key={k} label={k} />)}
                        </div>
                      ) : (
                        <span style={{ color: '#d1d5db', fontSize: '12px', fontStyle: 'italic' }}>
                          No keywords (exact name match)
                        </span>
                      )}
                    </td>
                    <td style={{ ...tdStyle, fontWeight: 600, color: '#059669' }}>
                      {proj.total_cost > 0
                        ? `₹${Number(proj.total_cost).toLocaleString('en-IN')}`
                        : <span style={{ color: '#d1d5db', fontWeight: 400, fontSize: '12px', fontStyle: 'italic' }}>—</span>
                      }
                    </td>
                    <td style={tdStyle}>
                      <span style={{
                        padding: '2px 8px', borderRadius: '10px', fontSize: '12px', fontWeight: 500,
                        background: proj.is_active ? '#dcfce7' : '#f3f4f6',
                        color: proj.is_active ? '#16a34a' : '#6b7280',
                      }}>
                        {proj.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        {/* Edit project */}
                        <button
                          style={iconBtnStyle('#667eea')}
                          onClick={() => setEditingProject({
                            id: proj.id,
                            name: proj.name,
                            description: proj.description || '',
                            keywords: proj.keywords,
                            total_cost: proj.total_cost,
                          })}
                        >
                          <Edit2 size={12} />
                          Edit
                        </button>
                        {/* Deactivate / Reactivate */}
                        {proj.is_active ? (
                          deletingId === proj.id ? (
                            <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
                              <span style={{ color: '#ef4444' }}>Deactivate?</span>
                              <button
                                style={{ ...iconBtnStyle('#ef4444'), fontWeight: 600 }}
                                onClick={() => handleDelete(proj.id)}
                              >Yes</button>
                              <button
                                style={iconBtnStyle('#6b7280')}
                                onClick={() => { setDeletingId(null); setDeleteConfirmName(''); }}
                              >No</button>
                            </span>
                          ) : (
                            <button
                              style={iconBtnStyle('#ef4444')}
                              onClick={() => { setDeletingId(proj.id); setDeleteConfirmName(proj.name); }}
                            >
                              <Trash2 size={12} />
                              Deactivate
                            </button>
                          )
                        ) : (
                          <button
                            style={iconBtnStyle('#059669')}
                            onClick={() => handleReactivate(proj.id)}
                          >
                            <RotateCcw size={12} />
                            Reactivate
                          </button>
                        )}
                      </div>
                    </td>
                    {/* Expand toggle */}
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      <button
                        style={{
                          background: 'none', border: 'none', cursor: 'pointer',
                          color: '#667eea', padding: '4px',
                        }}
                        title="Show developers"
                        onClick={() => setExpandedId(expandedId === proj.id ? null : proj.id)}
                      >
                        {expandedId === proj.id
                          ? <ChevronUp size={18} />
                          : <ChevronDown size={18} />
                        }
                      </button>
                    </td>
                  </tr>

                  {/* Developer breakdown row */}
                  {expandedId === proj.id && (
                    <tr style={{ background: '#f9fafb' }}>
                      <DevBreakdown projectId={proj.id} month={selectedMonth} />
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add project modal */}
      {showAddModal && (
        <ProjectModal
          mode="add"
          onClose={() => setShowAddModal(false)}
          onSave={handleCreate}
        />
      )}

      {/* Edit keywords modal */}
      {editingProject && (
        <ProjectModal
          mode="edit"
          project={editingProject}
          onClose={() => setEditingProject(null)}
          onSave={handleUpdate}
        />
      )}
    </div>
  );
}
