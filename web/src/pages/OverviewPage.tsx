import { useState } from "react";
import { useOverview } from "../api/queries";
import type { TimeRange } from "../api/types";
import { ActivityLineChart } from "../components/overview/ActivityLineChart";
import { ProjectBarChart } from "../components/overview/ProjectBarChart";
import { ProjectDonutChart } from "../components/overview/ProjectDonutChart";
import { SummaryStats } from "../components/overview/SummaryStats";
import { TimeRangeSelector } from "../components/overview/TimeRangeSelector";

export function OverviewPage() {
  const [range, setRange] = useState<TimeRange>("All time");
  const overview = useOverview(range);
  const data = overview.data;

  return (
    <section className="overview">
      <h1>Overview</h1>
      <TimeRangeSelector value={range} onChange={setRange} />

      {data && !data.empty && (
        <>
          <div className="overview-top">
            <ProjectDonutChart projects={data.projects} projectOrder={data.project_order} />
            <SummaryStats summary={data.summary} />
          </div>
          <ProjectBarChart projects={data.projects} projectOrder={data.project_order} />
          <ActivityLineChart activity={data.activity} />
        </>
      )}

      {data?.empty && (
        <p className="muted">
          {range === "All time"
            ? "No Claude session transcripts found."
            : `No sessions found for ${range.toLowerCase()}.`}
        </p>
      )}
    </section>
  );
}
