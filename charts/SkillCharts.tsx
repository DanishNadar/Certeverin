"use client";

import {Bar, BarChart, CartesianGrid, Cell, LabelList, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis} from "recharts";
import type {CertRecommendation, SkillStat} from "@/lib/api";

type ChartProps<T> = T & {darkMode?: boolean};

function chartTheme(darkMode = false) {
  return {
    axis: darkMode ? "#cbd5e1" : "#64748b",
    grid: darkMode ? "#334155" : "#dbe4f0",
    tooltipBg: darkMode ? "#0f172a" : "#ffffff",
    tooltipBorder: darkMode ? "#334155" : "#cbd5e1",
    tooltipText: darkMode ? "#e2e8f0" : "#10233f",
    primary: darkMode ? "#2dd4bf" : "#0f766e",
    ink: darkMode ? "#94a3b8" : "#10233f",
    gold: darkMode ? "#f59e0b" : "#b45309"
  };
}

const sampleSkills = [
  {name: "Python", frequency: 82, required_percent: 72, preferred_percent: 28},
  {name: "Cloud platforms", frequency: 68, required_percent: 64, preferred_percent: 36},
  {name: "SQL", frequency: 54, required_percent: 58, preferred_percent: 42},
  {name: "Model evaluation", frequency: 41, required_percent: 45, preferred_percent: 55}
];

function tooltipStyle(darkMode?: boolean) {
  const theme = chartTheme(darkMode);
  return {
    backgroundColor: theme.tooltipBg,
    borderColor: theme.tooltipBorder,
    color: theme.tooltipText,
    borderRadius: 6
  };
}

export function TopSkillsChart({skills, darkMode}: ChartProps<{skills: SkillStat[]}>) {
  const theme = chartTheme(darkMode);
  const data = skills.map((skill) => ({
    name: skill.skill,
    frequency: Math.round(skill.job_frequency * 100),
    required: skill.required_mentions,
    preferred: skill.preferred_mentions
  }));

  return (
    <div className="w-full" style={{height: Math.max(520, data.length * 34)}}>
      {data.length ? (
        <ResponsiveContainer>
          <BarChart data={data} layout="vertical" margin={{left: 24, right: 30, top: 8, bottom: 8}}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
            <XAxis type="number" unit="%" domain={[0, 100]} tick={{fill: theme.axis, fontSize: 12}} axisLine={{stroke: theme.grid}} tickLine={{stroke: theme.grid}} />
            <YAxis dataKey="name" type="category" width={150} tick={{fill: theme.axis, fontSize: 12}} axisLine={{stroke: theme.grid}} tickLine={false} />
            <Tooltip formatter={(value) => [`${value}%`, "Job postings"]} contentStyle={tooltipStyle(darkMode)} itemStyle={{color: theme.tooltipText}} labelStyle={{color: theme.tooltipText}} />
            <Bar dataKey="frequency" fill={theme.primary} radius={[0, 4, 4, 0]}>
              <LabelList dataKey="frequency" position="right" formatter={(value: number) => `${value}%`} fill={theme.axis} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <EmptyChartState title="Skills will appear here" description="A clean ranking preview will be replaced by measured demand once analysis finishes." variant="horizontal" darkMode={darkMode} />
      )}
    </div>
  );
}

export function RequiredPreferredChart({skills, darkMode}: ChartProps<{skills: SkillStat[]}>) {
  const theme = chartTheme(darkMode);
  const data = skills.map((skill) => {
    const totalMentions = skill.required_mentions + skill.preferred_mentions;
    return {
      skill: skill.skill,
      required_percent: totalMentions ? Math.round((skill.required_mentions / totalMentions) * 100) : 0,
      preferred_percent: totalMentions ? Math.round((skill.preferred_mentions / totalMentions) * 100) : 0,
      total_mentions: totalMentions
    };
  });
  return (
    <div className="w-full" style={{height: Math.max(420, data.length * 30)}}>
      {data.length ? (
        <ResponsiveContainer>
          <BarChart data={data} margin={{left: 0, right: 16, top: 10, bottom: 44}}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
            <XAxis dataKey="skill" tick={{fill: theme.axis, fontSize: 11}} angle={-25} textAnchor="end" interval={0} axisLine={{stroke: theme.grid}} tickLine={{stroke: theme.grid}} />
            <YAxis allowDecimals={false} unit="%" domain={[0, 100]} tick={{fill: theme.axis, fontSize: 12}} axisLine={{stroke: theme.grid}} tickLine={{stroke: theme.grid}} />
            <Tooltip formatter={(value) => [`${value}%`, "Mention share"]} contentStyle={tooltipStyle(darkMode)} itemStyle={{color: theme.tooltipText}} labelStyle={{color: theme.tooltipText}} />
            <Bar dataKey="required_percent" name="Required share" stackId="a" fill={theme.ink} />
            <Bar dataKey="preferred_percent" name="Preferred share" stackId="a" fill={theme.gold} />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <EmptyChartState title="Mention balance pending" description="Required and preferred evidence will be separated when section labels are detected." variant="vertical" darkMode={darkMode} />
      )}
    </div>
  );
}

export function CertificationScoreChart({certs, darkMode}: ChartProps<{certs: CertRecommendation[]}>) {
  const theme = chartTheme(darkMode);
  const data = certs.map((cert) => ({
    name: cert.certification_name,
    provider: cert.provider,
    score: cert.score,
    covered: cert.covered_skills.length
  }));

  return (
    <div className="w-full" style={{height: Math.max(520, data.length * 46)}}>
      {data.length ? (
        <ResponsiveContainer>
          <BarChart data={data} layout="vertical" margin={{left: 28, right: 42, top: 12, bottom: 12}}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
            <XAxis type="number" domain={[0, 100]} tick={{fill: theme.axis, fontSize: 12}} axisLine={{stroke: theme.grid}} tickLine={{stroke: theme.grid}} />
            <YAxis dataKey="name" type="category" width={220} tick={{fill: theme.axis, fontSize: 12}} axisLine={{stroke: theme.grid}} tickLine={false} />
            <Tooltip
              formatter={(value) => [`${value}%`, "Recommendation strength"]}
              contentStyle={tooltipStyle(darkMode)}
              itemStyle={{color: theme.tooltipText}}
              labelStyle={{color: theme.tooltipText}}
            />
            <Bar dataKey="score" name="Recommendation strength" radius={[0, 4, 4, 0]}>
              {data.map((entry, index) => (
                <Cell key={entry.name} fill={index === 0 ? theme.primary : theme.ink} />
              ))}
              <LabelList dataKey="score" position="right" formatter={(value: number) => `${value}%`} fill={theme.axis} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <EmptyChartState title="Certification ranking pending" description="Ranked recommendations will replace this preview after the job-market search." variant="horizontal" darkMode={darkMode} />
      )}
    </div>
  );
}

export function SkillCategoryChart({skills, darkMode}: ChartProps<{skills: SkillStat[]}>) {
  const theme = chartTheme(darkMode);
  const byCategory = skills.reduce<Record<string, number>>((rows, skill) => {
    rows[skill.category] = (rows[skill.category] ?? 0) + 1;
    return rows;
  }, {});
  const data = Object.entries(byCategory).map(([name, value]) => ({name, value}));
  return (
    <div className="h-80 w-full">
      {data.length ? (
        <ResponsiveContainer>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" outerRadius={105} label>
              {data.map((entry, index) => (
                <Cell key={entry.name} fill={[theme.primary, theme.ink, theme.gold, "#2563eb", "#7c3aed", "#64748b"][index % 6]} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => [`${value}`, "Skills"]} contentStyle={tooltipStyle(darkMode)} itemStyle={{color: theme.tooltipText}} labelStyle={{color: theme.tooltipText}} />
          </PieChart>
        </ResponsiveContainer>
      ) : (
        <EmptyChartState title="Category view pending" description="Discovered skills will be grouped into practical certification domains." variant="donut" darkMode={darkMode} />
      )}
    </div>
  );
}

export function CertificationProviderChart({certs, darkMode}: ChartProps<{certs: CertRecommendation[]}>) {
  const theme = chartTheme(darkMode);
  const data = Object.entries(
    certs.reduce<Record<string, number>>((rows, cert) => {
      rows[cert.provider] = (rows[cert.provider] ?? 0) + 1;
      return rows;
    }, {})
  ).map(([provider, count]) => ({provider, count}));

  return (
    <div className="h-80 w-full">
      {data.length ? (
        <ResponsiveContainer>
          <BarChart data={data} margin={{left: 8, right: 16, top: 12, bottom: 48}}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
            <XAxis dataKey="provider" tick={{fill: theme.axis, fontSize: 11}} angle={-25} textAnchor="end" interval={0} axisLine={{stroke: theme.grid}} tickLine={{stroke: theme.grid}} />
            <YAxis allowDecimals={false} tick={{fill: theme.axis, fontSize: 12}} axisLine={{stroke: theme.grid}} tickLine={{stroke: theme.grid}} />
            <Tooltip contentStyle={tooltipStyle(darkMode)} itemStyle={{color: theme.tooltipText}} labelStyle={{color: theme.tooltipText}} />
            <Bar dataKey="count" name="Certifications reviewed" fill={theme.primary} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <EmptyChartState title="Provider coverage pending" description="The catalog view will show which certification providers were included." variant="vertical" darkMode={darkMode} />
      )}
    </div>
  );
}

function EmptyChartState({title, description, variant, darkMode}: {title: string; description: string; variant: "horizontal" | "vertical" | "donut"; darkMode?: boolean}) {
  const theme = chartTheme(darkMode);

  return (
    <div className="flex h-full min-h-64 flex-col justify-center rounded-md border border-dashed border-slate-300 bg-slate-50 px-6 py-8 dark:border-slate-700 dark:bg-slate-950/50">
      <div className="mx-auto w-full max-w-sm">
        {variant === "horizontal" && (
          <div className="grid gap-3">
            {sampleSkills.map((item, index) => (
              <div key={item.name} className="grid grid-cols-[92px_1fr_34px] items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                <span>{item.name}</span>
                <span className="h-3 rounded-sm bg-slate-200 dark:bg-slate-800">
                  <span className="block h-full rounded-sm" style={{width: `${item.frequency}%`, backgroundColor: index === 0 ? theme.primary : theme.ink, opacity: index === 0 ? 0.9 : 0.7}} />
                </span>
                <span className="text-right">{item.frequency}%</span>
              </div>
            ))}
          </div>
        )}
        {variant === "vertical" && (
          <div className="flex h-32 items-end justify-center gap-4 border-b border-l border-slate-300 px-4 dark:border-slate-700">
            {sampleSkills.map((item, index) => (
              <span key={item.name} className="flex w-9 flex-col justify-end overflow-hidden rounded-t-sm bg-slate-200 dark:bg-slate-800" style={{height: `${Math.max(item.required_percent, 28)}%`}}>
                <span className="block w-full" style={{height: `${item.preferred_percent}%`, backgroundColor: theme.gold, opacity: 0.75}} />
                <span className="block w-full flex-1" style={{backgroundColor: index === 0 ? theme.primary : theme.ink, opacity: index === 0 ? 0.9 : 0.7}} />
              </span>
            ))}
          </div>
        )}
        {variant === "donut" && (
          <div className="mx-auto h-32 w-32 rounded-full" style={{background: `conic-gradient(${theme.primary} 0 38%, ${theme.ink} 38% 66%, ${theme.gold} 66% 82%, #64748b 82% 100%)`}}>
            <div className="relative left-1/2 top-1/2 h-16 w-16 -translate-x-1/2 -translate-y-1/2 rounded-full bg-slate-50 dark:bg-slate-950" />
          </div>
        )}
      </div>
      <div className="mx-auto mt-5 max-w-sm text-center">
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{title}</p>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
      </div>
    </div>
  );
}
