import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const number = value => new Intl.NumberFormat('en-US').format(value);
const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
const percent = value => value == null ? '—' : `${(value * 100).toFixed(1)}%`;
const dimensions = { loan_type: 'Loan type', region: 'Region', employment_type: 'Employment', age_band: 'Age band', income_band: 'Income band' };

async function get(path, signal) {
  const response = await fetch(`${API}${path}`, { signal });
  if (!response.ok) throw new Error(response.status === 503 ? 'Portfolio data has not been built on the backend.' : `API request failed (${response.status}).`);
  return response.json();
}

function App() {
  const [options, setOptions] = useState(null);
  const [filters, setFilters] = useState({ region: '', loan_type: '', employment_type: '' });
  const [dimension, setDimension] = useState('loan_type');
  const [summary, setSummary] = useState(null);
  const [groups, setGroups] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  const [accountId, setAccountId] = useState('');
  const [account, setAccount] = useState(null);
  const [risk, setRisk] = useState(null);
  const [riskError, setRiskError] = useState('');
  const [modelMetrics, setModelMetrics] = useState(null);
  const [accountError, setAccountError] = useState('');
  const [accountLoading, setAccountLoading] = useState(false);
  const [anomalies, setAnomalies] = useState(null);
  const [anomalyPage, setAnomalyPage] = useState(0);
  const [anomalyError, setAnomalyError] = useState('');
  const [reviewBusy, setReviewBusy] = useState('');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [askError, setAskError] = useState('');
  const [asking, setAsking] = useState(false);

  async function askPortfolio(event) {
    event.preventDefault();
    if (!question.trim()) return;
    setAsking(true); setAskError(''); setAnswer(null);
    try {
      const response = await fetch(`${API}/api/assistant/ask`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: question.trim() }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Could not answer that question.');
      setAnswer(result);
    } catch (err) { setAskError(err.message); }
    finally { setAsking(false); }
  }

  async function loadAnomalies(page = anomalyPage) {
    try { setAnomalies(await get(`/api/anomalies?limit=20&offset=${page * 20}`)); setAnomalyError(''); }
    catch (err) { setAnomalyError(err.message); }
  }

  useEffect(() => { loadAnomalies(anomalyPage); }, [anomalyPage]);

  async function reviewAnomaly(id, decision) {
    setReviewBusy(id); setAnomalyError('');
    try {
      const response = await fetch(`${API}/api/anomalies/${encodeURIComponent(id)}/review`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ decision }),
      });
      if (!response.ok) throw new Error('Unable to save review. Check the backend and review storage.');
      await loadAnomalies();
    } catch (err) { setAnomalyError(err.message); }
    finally { setReviewBusy(''); }
  }

  useEffect(() => { get('/api/model/metrics').then(setModelMetrics).catch(() => setModelMetrics(null)); }, []);

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
    const breakdownParams = new URLSearchParams(params);
    breakdownParams.set('dimension', dimension);
    setLoading(true); setError('');
    Promise.all([get('/api/portfolio/filters', controller.signal), get(`/api/portfolio/summary?${params}`, controller.signal), get(`/api/portfolio/breakdown?${breakdownParams}`, controller.signal)])
      .then(([filterData, summaryData, breakdown]) => { setOptions(filterData); setSummary(summaryData); setGroups(breakdown.groups); })
      .catch(err => { if (err.name !== 'AbortError') setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [filters, dimension, retry]);

  async function searchAccount(event) {
    event.preventDefault();
    if (!accountId.trim()) return;
    setAccountError(''); setRiskError(''); setRisk(null); setAccount(null); setAccountLoading(true);
    try {
      const id = encodeURIComponent(accountId.trim());
      setAccount(await get(`/api/accounts/${id}`));
      try { setRisk(await get(`/api/accounts/${id}/risk`)); }
      catch { setRiskError('Risk score is unavailable. Train the model on the backend first.'); }
    }
    catch (err) { setAccountError(err.message === 'API request failed (404).' ? 'No account found for that ID.' : err.message); }
    finally { setAccountLoading(false); }
  }

  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="#overview"><span className="brand-mark">◈</span><span>Northstar <b>Risk</b></span></a><div className="top-right"><span className="environment"><i /> SYNTHETIC DATA</span><span className="avatar">CR</span></div></header>
    <div className="layout"><aside className="sidebar"><div className="nav-caption">WORKSPACE</div><a className="nav-item active" href="#overview"><span>▦</span> Portfolio overview</a><a className="nav-item" href="#account"><span>⌕</span> Account explorer</a><a className="nav-item" href="#anomalies"><span>◉</span> Anomaly review</a><div className="sidebar-note"><span className="note-icon">✦</span><strong>Built for clarity.</strong><p>Explore the portfolio and understand the numbers behind the risk.</p></div><div className="sidebar-foot">CREDIT RISK ANALYTICS <span>V 0.1</span></div></aside>
    <main id="overview"><div className="breadcrumb">WORKSPACE <span>/</span> PORTFOLIO OVERVIEW</div><div className="page-title"><div><div className="eyebrow"><span /> PORTFOLIO INTELLIGENCE</div><h1>A clearer view of risk<span>.</span></h1><p>Explore your lending portfolio and understand what’s driving performance.</p></div><div className="data-label"><span className="pulse" /> Live portfolio data <small>From supplied synthetic dataset</small></div></div>
      <section className="filter-panel" aria-label="Portfolio filters"><div className="filter-heading"><div><strong>Refine your view</strong><small>Filters apply across the overview</small></div><button className="text-button" onClick={() => setFilters({ region: '', loan_type: '', employment_type: '' })}>Reset filters ↗</button></div><div className="filters">{[['region','Region'],['loan_type','Loan type'],['employment_type','Employment type']].map(([key,label]) => <label key={key}>{label}<select value={filters[key]} onChange={e => setFilters({ ...filters, [key]: e.target.value })}><option value="">All {label.toLowerCase()}s</option>{options?.[key]?.map(option => <option key={option}>{option}</option>)}</select></label>)}</div></section>
      {error && <div className="error" role="alert"><strong>Couldn’t load portfolio data.</strong> {error} Check that the backend is running. <button onClick={() => setRetry(x => x + 1)}>Try again</button></div>}
      <div className="section-header"><div><div className="section-kicker">THE BIG PICTURE</div><h2>Portfolio at a glance</h2></div><span className="section-meta">ACCOUNT-LEVEL VIEW</span></div>
      <section className="metrics" aria-busy={loading}>{[['Total accounts', summary && number(summary.accounts), 'Loan accounts in selection'],['Customers', summary && number(summary.customers), 'Distinct borrowers'],['Observed default rate', summary && percent(summary.default_rate), summary ? `${number(summary.defaulted_accounts)} defaulted accounts` : 'Historical outcome'],['Original loan amount', summary && money(summary.original_loan_amount), 'Not current outstanding balance']].map(([label,value,note], index) => <div className="metric" key={label}><div className="metric-head">{label}<span>{['▤','♧','↗','◫'][index]}</span></div><div className="metric-value">{loading ? '—' : (value ?? '—')}</div><div className="metric-foot"><span /> {note}</div></div>)}</section>
      <section className="analysis-grid"><div className="card breakdown"><div className="card-header"><div><div className="section-kicker">PORTFOLIO COMPOSITION</div><h2>Default rate by segment</h2><p>Compare observed defaults across portfolio dimensions.</p></div><label className="dimension-label"><span className="sr-only">Breakdown dimension</span><select value={dimension} onChange={e => setDimension(e.target.value)}>{Object.entries(dimensions).map(([value,label]) => <option value={value} key={value}>{label}</option>)}</select></label></div><div className="chart-header"><span>SEGMENT</span><span>DEFAULT RATE</span></div><div className="chart">{!loading && groups.length === 0 && <p className="empty">No accounts match these filters.</p>}{groups.map(group => <div className="bar-row" key={group.label}><div className="bar-label">{group.label}<small>{number(group.accounts)} accounts</small></div><div className="bar-track"><div className="bar-fill" style={{ width: `${Math.min(group.default_rate * 100, 100)}%` }} /></div><strong>{percent(group.default_rate)}</strong></div>)}</div><div className="chart-caption"><span /> Observed default rate <span className="caption-end">Share of accounts in each segment</span></div></div>
      <div className="card context-card"><div className="section-kicker">A NOTE ON THE DATA</div><h2>Context matters.</h2><p>This is a synthetic portfolio. The figures shown reflect recorded outcomes in the supplied data, not predictions.</p><div className="context-divider" /><div className="context-row"><span>01</span><div><strong>Account-based metrics</strong><p>Default rates count loan accounts, while customer totals count unique borrowers.</p></div></div><div className="context-row"><span>02</span><div><strong>Exposure measure</strong><p>Loan amount represents original lending, not today’s outstanding balance.</p></div></div><div className="context-tag">◈ &nbsp; DATA TRANSPARENCY</div></div></section>
      <section className="card account-card" id="account"><div className="card-header"><div><div className="section-kicker">ACCOUNT EXPLORER</div><h2>Look closer at an account</h2><p>Enter an account ID to view its recorded details and exploratory model score.</p></div></div><form className="account-form" onSubmit={searchAccount}><label className="sr-only" htmlFor="account-id">Account ID</label><input id="account-id" placeholder="e.g. ACC200001" value={accountId} onChange={e => setAccountId(e.target.value)} /><button disabled={accountLoading}>{accountLoading ? 'Searching…' : 'Find account →'}</button></form>{accountError && <p className="account-error" role="alert">{accountError}</p>}{account && <div className="account-results">{[['Account',account.account_id],['Loan type',account.loan_type],['Loan amount',money(account.loan_amount)],['Recorded outcome',account.target_default === 1 ? 'Defaulted' : 'Performing'],['Missed payments',number(account.missed_payments)],...(risk ? [['Exploratory score',percent(risk.probability)],['Evaluation group',risk.evaluation_group === 'training' ? 'Training (in-sample)' : 'Held-out']] : [])].map(([key,value]) => <div key={key}><small>{key}</small><strong>{value}</strong></div>)}{risk && <p>Largest model contributions: {risk.drivers.map(driver => `${driver.feature.replace(/^(num|cat)__/, '').replaceAll('_', ' ')} (${driver.log_odds_contribution >= 0 ? '+' : '−'})`).join(', ')}. Signs indicate effects on model log-odds, not causes.</p>}<p>{riskError || 'Exploratory only: missing outcome and bureau snapshot dates mean data leakage cannot be ruled out. Not a credit decision.'}</p></div>}</section>
      {modelMetrics && <section className="card account-card"><div className="section-kicker">MODEL VALIDATION</div><h2>Exploratory model comparison</h2><p className="model-note">Customer-grouped held-out set · AUC, KS and Gini. Scores use logistic regression.</p><div className="model-grid">{Object.entries(modelMetrics.models).map(([name, m]) => <div className="model-item" key={name}><strong>{name.replaceAll('_',' ')}</strong><p>AUC <b>{m.auc.toFixed(3)}</b> &nbsp; KS <b>{m.ks.toFixed(3)}</b> &nbsp; Gini <b>{m.gini.toFixed(3)}</b></p></div>)}</div><p className="model-note">{modelMetrics.limitation}</p></section>}
      <section className="card account-card" id="assistant"><div className="section-kicker">ASK THE PORTFOLIO</div><h2>Ask a question about the data</h2><p className="model-note">Try “Which loan type has the highest default rate?” The assistant supports portfolio counts, default rates and original loan amounts, by one dimension at a time.</p><form className="account-form" onSubmit={askPortfolio}><label className="sr-only" htmlFor="question">Portfolio question</label><input id="question" value={question} maxLength={500} onChange={e => setQuestion(e.target.value)} placeholder="Ask about this portfolio" /><button disabled={asking}>{asking ? 'Thinking…' : 'Ask →'}</button></form>{askError && <p className="account-error" role="alert">{askError}</p>}{answer && <div className="assistant-answer"><strong>{answer.answer}</strong>{answer.source && <p>Source: {answer.source} · Filters: {Object.keys(answer.filters || {}).length ? JSON.stringify(answer.filters) : 'All accounts'}</p>}{answer.definition && <p>{answer.definition}</p>}</div>}<p className="model-note">Triggered by submitting a question. A false positive is an incorrect interpretation that still produces an answer; a false negative is a valid question declined. Check the metric, filters and source before acting. Answers are calculated from the dataset, but interpretation may be wrong.</p></section>
      <section className="card account-card" id="anomalies"><div className="section-kicker">HUMAN REVIEW</div><h2>Unusual account activity</h2><p className="model-note">Isolation Forest flags approximately 5% of accounts in each loan type with unusual repayment or bureau patterns. {anomalies?.flagged_count ?? '—'} flags, ordered by anomaly score.</p><p className="model-note">A false positive is a legitimate unusual account; a false negative is a concerning account not flagged. An analyst must investigate and confirm or dismiss each flag. Percentiles compare accounts of the same loan type and provide context, not a causal explanation of the model.</p>{anomalyError && <p className="account-error" role="alert">{anomalyError}</p>}<div className="anomaly-list">{anomalies?.accounts.map(item => <div className="anomaly-row" key={item.account_id}><div><strong>{item.account_id}</strong> <span className="anomaly-type">{item.loan_type} · score {item.anomaly_score.toFixed(3)}</span><p>{item.reasons.map(reason => `${reason.feature}: ${number(reason.value)} (${reason.peer_percentile}th peer percentile)`).join(' · ') || 'Unusual combination of features'}</p><small>Review: {item.review?.decision || 'Pending'}</small></div><div className="review-actions"><button disabled={reviewBusy === item.account_id} onClick={() => reviewAnomaly(item.account_id,'confirmed')}>Confirm</button><button disabled={reviewBusy === item.account_id} onClick={() => reviewAnomaly(item.account_id,'dismissed')}>Dismiss</button></div></div>)}</div><div className="review-actions"><button disabled={anomalyPage === 0} onClick={() => setAnomalyPage(p => p - 1)}>Previous</button><span>Page {anomalyPage + 1}</span><button disabled={!anomalies || (anomalyPage + 1) * 20 >= anomalies.flagged_count} onClick={() => setAnomalyPage(p => p + 1)}>Next</button></div></section>
      <footer><span>© CREDIT RISK PORTFOLIO ANALYTICS</span><span>Designed for informed decisions <b>✳</b></span></footer>
    </main></div></div>;
}

createRoot(document.getElementById('root')).render(<App />);
