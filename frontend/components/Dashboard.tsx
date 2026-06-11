"use client";

import {useState} from "react";
import {Award, Download, ExternalLink, FileText, Moon, Play, RefreshCw, Search, Sun} from "lucide-react";
import {generateReport, createRun, getCertifications, getSkills, API_BASE, type CertRecommendation, type SearchRun, type SkillStat} from "@/lib/api";
import {CertificationProviderChart, CertificationScoreChart, RequiredPreferredChart, SkillCategoryChart, TopSkillsChart} from "@/charts/SkillCharts";

const SOURCE_OPTIONS = ["adzuna", "usajobs", "greenhouse", "lever"];
const DEFAULT_SOURCE_LIMITS: Record<string, number> = {
  adzuna: 250,
  usajobs: 250,
  greenhouse: 250,
  lever: 250
};

function formatPercent(value: number) {
  return `${value.toFixed(1)}%`;
}

function providerInitials(provider: string) {
  return provider.split(/\s+/).map((word) => word[0]).join("").slice(0, 3).toUpperCase();
}

export function Dashboard() {
  const [title, setTitle] = useState("AI Engineer");
  const [related, setRelated] = useState("Machine Learning Engineer, MLOps Engineer, Cloud AI Engineer");
  const [location, setLocation] = useState("United States");
  const [seniority, setSeniority] = useState("all");
  const [sources, setSources] = useState<string[]>(["adzuna", "usajobs"]);
  const [sourceLimits, setSourceLimits] = useState<Record<string, number>>(DEFAULT_SOURCE_LIMITS);
  const [run, setRun] = useState<SearchRun | null>(null);
  const [skills, setSkills] = useState<SkillStat[]>([]);
  const [certs, setCerts] = useState<CertRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [reportUrl, setReportUrl] = useState("");
  const [darkMode, setDarkMode] = useState(false);
  const totalRequested = sources.reduce((total, source) => total + (sourceLimits[source] ?? DEFAULT_SOURCE_LIMITS[source] ?? 25), 0);

  async function startAnalysis() {
    setLoading(true);
    setError("");
    setReportUrl("");
    try {
      const nextRun = await createRun({
        target_title: title,
        related_titles: related.split(",").map((item) => item.trim()).filter(Boolean),
        location,
        seniority,
        limit: totalRequested,
        source_limits: Object.fromEntries(sources.map((source) => [source, sourceLimits[source] ?? DEFAULT_SOURCE_LIMITS[source] ?? 25])),
        sources,
        output_format: "both"
      });
      setRun(nextRun);
      const [skillRows, certRows] = await Promise.all([getSkills(nextRun.id), getCertifications(nextRun.id)]);
      setSkills(skillRows);
      setCerts(certRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  async function exportPdf() {
    if (!run) return;
    setLoading(true);
    setError("");
    try {
      const report = await generateReport(run.id);
      setReportUrl(`${API_BASE}${report.download_url}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report generation failed.");
    } finally {
      setLoading(false);
    }
  }

  function toggleSource(source: string) {
    setSources((current) => current.includes(source) ? current.filter((item) => item !== source) : [...current, source]);
  }

  function updateSourceLimit(source: string, value: number) {
    const nextValue = Number.isFinite(value) ? Math.min(Math.max(Math.round(value), 1), 10000) : DEFAULT_SOURCE_LIMITS[source];
    setSourceLimits((current) => ({...current, [source]: nextValue}));
  }

  const topCert = certs[0];
  const hasResults = Boolean(run && skills.length && certs.length);

  const textSubtle = "text-slate-600 dark:text-slate-300";
  const textMuted = "text-slate-500 dark:text-slate-400";

  return (
    <main className={darkMode ? "dark min-h-screen bg-slate-950 text-slate-100" : "min-h-screen bg-slate-50 text-ink"}>
      <header className="border-b border-ink/10 bg-ink text-white dark:border-slate-800 dark:bg-slate-950">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.18em] text-teal-200">Certeverin</p>
            <h1 className="text-2xl font-semibold">Find role-relevant certifications from job postings</h1>
            <p className="mt-1 max-w-3xl text-sm text-slate-200">Search a role, extract the most requested skills, then rank certifications by how well they cover that demand.</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button onClick={startAnalysis} className="focus-ring inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:opacity-60" disabled={loading}>
              {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {loading ? "Searching..." : "Search job postings"}
            </button>
            <button
              onClick={() => setDarkMode((value) => !value)}
              aria-label={darkMode ? "Switch to light mode" : "Switch to dark mode"}
              className="focus-ring inline-flex items-center gap-2 rounded-md border border-white/20 bg-white/5 px-3 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              {darkMode ? "Light mode" : "Dark mode"}
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-6 lg:grid-cols-[360px_1fr]">
        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/95">
          <div className="mb-4 flex items-center gap-2">
            <Search className="h-5 w-5 text-accent dark:text-teal-300" />
            <h2 className="text-lg font-semibold">Job Posting Search</h2>
          </div>
          <label className="mb-3 block text-sm font-medium">Target job title
            <input value={title} onChange={(event) => setTitle(event.target.value)} className="focus-ring mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-ink shadow-sm placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500" />
          </label>
          <label className="mb-3 block text-sm font-medium">Related titles
            <textarea value={related} onChange={(event) => setRelated(event.target.value)} className="focus-ring mt-1 min-h-20 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-ink shadow-sm placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500" />
          </label>
          <label className="mb-3 block text-sm font-medium">Location
            <input value={location} onChange={(event) => setLocation(event.target.value)} className="focus-ring mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-ink shadow-sm placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500" />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm font-medium">Seniority
              <select value={seniority} onChange={(event) => setSeniority(event.target.value)} className="focus-ring mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-ink shadow-sm dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
                {["all", "internship", "entry-level", "associate", "mid-level", "senior"].map((item) => <option key={item}>{item}</option>)}
              </select>
            </label>
            <Metric label="Requested postings" value={totalRequested.toLocaleString()} compact />
          </div>
          <div className="mt-4">
            <div className="mb-2 flex items-end justify-between gap-3">
              <p className="text-sm font-medium">Sources and posting targets</p>
              <p className={`text-xs ${textMuted}`}>Higher values may take longer</p>
            </div>
            {SOURCE_OPTIONS.map((source) => (
              <div key={source} className="mb-2 grid grid-cols-[1fr_116px] items-center gap-3 text-sm">
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={sources.includes(source)} onChange={() => toggleSource(source)} className="h-4 w-4 accent-teal-700" />
                  <span className="capitalize">{source}</span>
                </label>
                <input
                  aria-label={`${source} posting target`}
                  type="number"
                  min={1}
                  max={10000}
                  value={sourceLimits[source] ?? DEFAULT_SOURCE_LIMITS[source]}
                  onChange={(event) => updateSourceLimit(source, Number(event.target.value))}
                  className="focus-ring w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-right text-ink shadow-sm disabled:bg-slate-50 disabled:text-slate-400 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:disabled:bg-slate-900 dark:disabled:text-slate-500"
                  disabled={!sources.includes(source)}
                />
              </div>
            ))}
          </div>
          <button onClick={startAnalysis} className="focus-ring mt-5 inline-flex w-full items-center justify-center gap-2 rounded-md bg-accent px-4 py-3 font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:opacity-60" disabled={loading || !title.trim() || !sources.length}>
            {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            {loading ? "Analyzing postings..." : "Search and rank certifications"}
          </button>
          {!sources.length && <p className="mt-2 text-sm text-red-700 dark:text-red-300">Choose at least one source.</p>}
          {error && <p className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/70 dark:bg-red-950/50 dark:text-red-200">{error}</p>}
          {run?.summary.collection_warning && <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-200">{run.summary.collection_warning}</p>}
        </section>

        <section className="space-y-6">
          {!hasResults && (
            <section className="rounded-lg border border-teal-200 bg-teal-50 p-5 text-teal-950 shadow-sm dark:border-teal-800 dark:bg-teal-950/40 dark:text-teal-50">
              <div className="flex gap-3">
                <Award className="mt-1 h-5 w-5 shrink-0 text-accent dark:text-teal-300" />
                <div>
                  <h2 className="text-lg font-semibold">Start with a role search</h2>
                  <p className="mt-1 text-sm text-teal-900 dark:text-teal-100">Use the form on the left to search postings. When the run finishes, this page will show demanded skills, certification rankings, and source-backed evidence.</p>
                </div>
              </div>
            </section>
          )}

          <div className="grid gap-4 md:grid-cols-4">
            <Metric label="Jobs analyzed" value={String(run?.summary.jobs_analyzed ?? 0)} />
            <Metric label="Skills found" value={String(skills.length)} />
            <Metric label="Certifications scored" value={String(certs.length)} />
            <Metric label="Requested postings" value={(run?.limit ?? totalRequested).toLocaleString()} />
          </div>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/95">
            <h2 className="text-xl font-semibold">Executive Summary</h2>
            <p className={`mt-2 ${textSubtle}`}>{run?.summary.recommendation ?? "Start an analysis to generate certification recommendations grounded in job-posting skill demand."}</p>
            {run?.summary.recommendations?.length ? (
              <ol className={`mt-4 grid gap-2 text-sm ${textSubtle}`}>
                {run.summary.recommendations.map((item) => <li key={item}>{item}</li>)}
              </ol>
            ) : null}
            {topCert && (
              <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
                <div>
                  <p className={`text-sm uppercase tracking-wide ${textMuted}`}>Top recommendation</p>
                  <h3 className="text-lg font-semibold">{topCert.certification_name}</h3>
                  <p className={`text-sm ${textSubtle}`}>{topCert.provider} • {topCert.status} • score {formatPercent(topCert.score)}</p>
                </div>
                <button onClick={exportPdf} className="focus-ring inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 font-semibold text-white transition hover:bg-slate-800 dark:bg-teal-700 dark:hover:bg-teal-600">
                  <FileText className="h-4 w-4" />
                  Export PDF
                </button>
              </div>
            )}
            {reportUrl && <a className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-accent" href={reportUrl}><Download className="h-4 w-4" />Download generated report</a>}
          </section>

          <div className="grid gap-6 xl:grid-cols-2">
            <ChartCard title="All Requested Skills" note="This chart shows the share of analyzed postings that mention each skill.">
              <TopSkillsChart skills={skills} darkMode={darkMode} />
            </ChartCard>
            <ChartCard title="Required vs Preferred Mentions" note="Darker bars represent required-section mentions; gold bars represent preferred-section mentions when section labels were detected.">
              <RequiredPreferredChart skills={skills} darkMode={darkMode} />
            </ChartCard>
            <ChartCard title="Skill Categories" note="Shows how the discovered skills cluster across technical categories.">
              <SkillCategoryChart skills={skills} darkMode={darkMode} />
            </ChartCard>
            <ChartCard title="Certification Providers Reviewed" note="Shows provider coverage across every certification in the catalog.">
              <CertificationProviderChart certs={certs} darkMode={darkMode} />
            </ChartCard>
          </div>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/95">
            <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <div>
                <h2 className="text-xl font-semibold">Important Certifications for {run?.target_title ?? title}</h2>
                <p className={`mt-1 text-sm ${textSubtle}`}>Higher recommendation-strength percentages mean stronger coverage of demanded skills, role alignment, provider signal, cost-benefit, accessibility, and source confidence.</p>
              </div>
              {topCert && <p className="rounded-md bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-900 dark:bg-teal-950 dark:text-teal-100">Top pick: {topCert.certification_name}</p>}
            </div>
            <CertificationScoreChart certs={certs} darkMode={darkMode} />
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[760px] border-collapse text-sm">
                <thead className="bg-slate-100 text-left dark:bg-slate-950">
                  <tr>
                    <th className="p-3">Rank</th>
                    <th className="p-3">Certification</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Score</th>
                    <th className="p-3">Covered demanded skills</th>
                  </tr>
                </thead>
                <tbody>
                  {certs.map((cert, index) => (
                    <tr key={cert.certification_name} className="border-t border-slate-200 dark:border-slate-800">
                      <td className="p-3">{index + 1}</td>
                      <td className="p-3 font-medium">
                        <div className="flex items-center gap-3">
                          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-slate-100 text-xs font-bold text-ink dark:bg-slate-800 dark:text-slate-100">{providerInitials(cert.provider)}</span>
                          <div>
                            <a href={cert.official_url} className="inline-flex items-center gap-1 text-accent underline decoration-teal-300 underline-offset-4 dark:text-teal-300" target="_blank" rel="noreferrer">{cert.certification_name}<ExternalLink className="h-3 w-3" /></a>
                            <p className={`font-normal ${textMuted}`}>{cert.provider} official certification page</p>
                          </div>
                        </div>
                      </td>
                      <td className="p-3">{cert.status}</td>
                      <td className="p-3 font-semibold">{formatPercent(cert.score)}</td>
                      <td className="p-3">{cert.covered_skills.join(", ") || "No top skills covered"}</td>
                    </tr>
                  ))}
                  {!certs.length && (
                    <tr className="border-t border-slate-200 dark:border-slate-800">
                      <td className={`p-3 ${textMuted}`} colSpan={5}>Run a job posting search to populate certification rankings.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/95">
            <h2 className="text-xl font-semibold">Skill Explorer</h2>
            <div className="mt-4 grid gap-3">
              {skills.map((skill) => (
                <details key={skill.skill} className="rounded-md border border-slate-200 p-3 dark:border-slate-800 dark:bg-slate-950/40">
                  <summary className="cursor-pointer font-semibold">{skill.skill} • {(skill.job_frequency * 100).toFixed(0)}% of jobs</summary>
                  <p className={`mt-2 text-sm ${textSubtle}`}>Category: {skill.category}. Confidence: {(skill.confidence * 100).toFixed(0)}%.</p>
                  {skill.snippets.map((snippet, index) => <p key={index} className={`mt-2 border-l-4 border-teal-600 pl-3 text-sm ${textSubtle}`}>{snippet}</p>)}
                </details>
              ))}
              {!skills.length && <EmptyPanel title="No skills analyzed yet" description="Skill evidence, categories, confidence scores, and source snippets will appear here after a search completes." />}
            </div>
          </section>
        </section>
      </div>
    </main>
  );
}

function Metric({label, value, compact = false}: {label: string; value: string; compact?: boolean}) {
  return (
    <div className={compact ? "rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-950/60" : "rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900/95"}>
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      <p className={compact ? "mt-1 text-lg font-semibold" : "mt-1 text-2xl font-semibold"}>{value}</p>
    </div>
  );
}

function ChartCard({title, note, children}: {title: string; note: string; children: React.ReactNode}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/95">
      <h2 className="text-xl font-semibold">{title}</h2>
      {children}
      <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">{note}</p>
    </section>
  );
}

function EmptyPanel({title, description}: {title: string; description: string}) {
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/50">
      <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{title}</p>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
    </div>
  );
}
