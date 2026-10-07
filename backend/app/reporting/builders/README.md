## Reporting Builders

Responsibility: Compose the immutable Generation Context into structured report documents — the Summary and Detailed variants — as sections, labelled values and figure references.
Inputs: One `GenerationContext`, plus the stored visualization published by the visualization stage (or the reason there is none).
Outputs: One `ReportDocument` per variant: ordered `ReportSection`s, each value carrying its own availability and placeholder.
Dependencies: `app.reporting.context`, `app.reporting.models`, `app.reporting.constants`.

Builders emit **data, never markup** — no HTML, CSS, or layout decisions live here. Both variants use the same section builders, so they can never state different facts; they differ only in which sections they include and at what depth. Sections whose data source is the Signal Processing module keep their place in the layout and carry the standardized placeholder instead of an invented value.
