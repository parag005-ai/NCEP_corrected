## Reporting Templates

Responsibility: Hold the approved report templates, resolve them by report type, and bind composed report documents into them.
Inputs: A `ReportDocument` from the builders, the resolved `TemplateDefinition`, the report identity, and the stored ECG figure.
Outputs: A `RenderedReport` carrying the canonical HTML plus the template identity it was produced from.
Dependencies: `app.reporting.builders`, `app.reporting.constants`, `app.reporting.exceptions`, Jinja2.

`detailed_report.html.j2` is the approved Detailed Report specification made data-driven: structure, ordering, layout and class names are unchanged, and every displayed value is bound from the report document. `assets/report.css` is the approved stylesheet, held verbatim and inlined at render time so a generated report is one self-contained file.

The engine adds no content. A value the document reports as unavailable renders the standardized placeholder the builders attached to it — never a sample value. The Summary Report is presented by the NCEP frontend, which owns its layout; the registry versions the structured data contract produced for it.
