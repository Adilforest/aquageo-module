import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import "../../i18n";
import ReportsBlock, { reportUrl } from "./ReportsBlock";

describe("reportUrl", () => {
  it("targets the condition-summary endpoint with the format", () => {
    const url = reportUrl("pdf", new URLSearchParams());
    expect(url).toContain("/api/v1/reports/condition-summary/");
    expect(url).toContain("format=pdf");
  });

  it("carries the active map filters, including multi-value ones", () => {
    const filters = new URLSearchParams();
    filters.append("type", "dam");
    filters.append("type", "canal");
    filters.append("condition", "emergency");
    filters.set("basin", "b-1");
    const url = reportUrl("xlsx", filters);
    expect(url).toContain("format=xlsx");
    expect(url).toContain("type=dam");
    expect(url).toContain("type=canal");
    expect(url).toContain("condition=emergency");
    expect(url).toContain("basin=b-1");
  });

  it("ignores params that are not report filters", () => {
    const filters = new URLSearchParams("zoom=12&type=dam");
    const url = reportUrl("pdf", filters);
    expect(url).not.toContain("zoom=12");
    expect(url).toContain("type=dam");
  });
});

function renderAt(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <ReportsBlock />
    </MemoryRouter>,
  );
}

describe("ReportsBlock", () => {
  it("renders the block with PDF and Excel export buttons", () => {
    renderAt("/dashboard");
    const pdf = screen.getByTestId("report-pdf") as HTMLAnchorElement;
    const xlsx = screen.getByTestId("report-xlsx") as HTMLAnchorElement;
    expect(pdf).toBeTruthy();
    expect(xlsx).toBeTruthy();
    expect(pdf.getAttribute("href")).toContain(
      "/api/v1/reports/condition-summary/?format=pdf",
    );
    expect(xlsx.getAttribute("href")).toContain("format=xlsx");
  });

  it("reflects the current URL filters in the export links", () => {
    renderAt("/dashboard?type=dam&condition=repair&basin=b-9");
    const pdf = screen.getByTestId("report-pdf") as HTMLAnchorElement;
    const href = pdf.getAttribute("href") ?? "";
    expect(href).toContain("type=dam");
    expect(href).toContain("condition=repair");
    expect(href).toContain("basin=b-9");
    expect(href).toContain("format=pdf");
  });
});
