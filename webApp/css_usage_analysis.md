# CSS Usage Analysis for WebApp

## Summary of CSS Selectors Found in HTML Files

### Classes Used in HTML Templates:

#### Layout & Structure Classes:
- wrapper
- sidebar
- sidebar-wrapper
- content
- content-box
- box
- box-wrapper
- box-calc
- dashboard-container
- navigation-container
- nav-container
- project-header
- project-overview-wrapper

#### Navigation Classes:
- nav
- nav-tabs
- nav-item
- nav-link
- nav-link-radio
- active
- collapsed
- nav-pills
- tab-content
- tab-pane
- fade
- show

#### Form & Input Classes:
- form
- form-check-input
- fieldWrapper
- button
- btn
- btn-primary
- btn-secondary

#### Table Classes:
- table
- table-sum
- table-dashboard
- dashboard-sensi-table
- value-cell
- red-cell
- red-dot
- selected
- selected-row
- clickable-row

#### Metric & Display Classes:
- metric-value
- metric-title
- overview-box
- overview-metrics-row
- overview-metrics-column
- metrics-row
- metrics-column
- metrics-container

#### Chart & Graph Classes:
- graph
- graph-dev
- charts-container
- chart-container
- financing-plan-container
- financing-plan-box
- box-wrapper-chart

#### Accordion Classes:
- accordion
- accordion-item
- accordion-header
- accordion-button
- accordion-body
- accordion-collapse

#### Row/Column Layout Classes:
- row-inline-wrapper
- row-inline-two
- row-inline-three
- row-inline-three-first
- row-inline-three-second
- row-inline-three-first-underlined
- row-inline-four
- columns-container
- column-input

#### Mode & State Classes:
- financing-mode-only
- hidden
- detailed
- operational_tabs
- mode-toggle-container
- toggle-label
- switch
- slider
- round

#### Summary/Scenario Classes:
- summary-container
- summary-scenario-left
- summary-scenario-right
- case-checkbox
- case-selection-container

#### Other Utility Classes:
- dates-wrapper
- title-wrapper
- year-box
- left
- right
- impact-positive
- impact-negative
- impact-indicator
- sensitivity-label
- logo
- logo-icon

### IDs Used in HTML Templates:

#### Main Layout IDs:
- sidebar
- sidebar-wrapper
- content
- content-box

#### Project & Overview IDs:
- project_name
- project-status-box
- ProjectStatus
- ProjectStatusLabel
- overview-wrapper
- metric-status

#### Form IDs:
- post-form
- accordionSidebar

#### Navigation Tab IDs:
- nav-summary
- nav-calculation
- nav-summary-charts
- nav-changelog
- nav-valuation
- nav-container-aligned-left
- sponsor-case-tab
- lender-case-tab

#### Table Container IDs:
- dates
- flags
- days
- time_series
- indexation
- production
- price
- revenues
- opex
- working_cap
- IS (Income Statement)
- op_account
- distr_account
- uses
- sources
- share_capital
- SHL
- senior_debt
- DSRA
- assets
- liabilities
- audit
- ratios

#### Dashboard Table IDs:
- dashboard-sensi-table-input
- dashboard-sensi-table-input-sensi
- dashboard-sensi-table-input-sponsor
- dashboard-sensi-table-input-sensi-sponsor
- summary_project
- summary_equity
- summary_debt
- summary_audit
- summary_valuation
- summary_sensi
- sponsor_summary_sensi

#### Chart IDs:
- chartCash
- chartCashFlow
- chartDSCR
- chartDSRA
- chartDebtOut
- chartDebtS
- chartEqtFlow
- chartFinPlan
- chartOpRevenuesbyCountry
- chartOpRevenuesbyTech
- chartProduction
- chartProjectCosts
- chartSources
- chartUses

#### Metric Display IDs:
- capacity
- total_uses
- sponsor_IRR
- gearing
- lender_DSCR
- installed_capacity
- senior_debt
- debtMaturity

#### Date IDs:
- dateCOD
- dateLiquidation
- dateRetirement

#### Sensitivity IDs:
- sensi_production
- sensi_inflation
- sensi_opex
- sponsor_sensi_production
- sponsor_sensi_inflation
- sponsor_sensi_opex

#### Modal IDs:
- loading-modal
- ArchTaxModal
- CFEModal
- DevTaxModal
- PTaxModal

#### Other IDs:
- myDropdown
- searchInput
- searchInput2
- sumConstructionCosts
- sumSeasonality

### CSS Selectors Referenced in style.css but Not Found in HTML:

These selectors exist in the CSS but were not found in the HTML templates scanned:

1. **Element-specific selectors with custom tags:**
   - h1-calc, h2-calc, h3-calc (custom heading tags)
   - title-wrapper (as an element, not class)

2. **Table-specific IDs not found:**
   - #table-financing-terms
   - #BS_a (Balance Sheet)
   - #table_sum_sources
   - #table_sum_uses
   - #table-scenario-input
   - #table-scenario-output
   - #table-sponsor-scenario-input
   - #table-sponsor-scenario-output

3. **Class selectors potentially unused:**
   - .nav-link-radio
   - .container-nav
   - .nav-summary
   - .summary-titles
   - .summary
   - .modal-backdrop
   - .dashboard_sidebar_separator
   - .input-sensi-table

4. **ID selectors potentially unused:**
   - #shango
   - #sidebarCollapse
   - #summary-fp
   - #summary-financing
   - #summary-IRR
   - #summary-debt
   - #summary-audit
   - #summary-sensitivities

### Recommendations:

1. **Potentially unused CSS** - The following CSS rules may be candidates for removal:
   - Rules for table IDs that don't appear in the HTML (#BS_a, #CF_a, etc.)
   - Some specialized class selectors that weren't found in templates
   - Custom element selectors (h1-calc, h2-calc, etc.) if they're not dynamically generated

2. **Dynamic content consideration** - Some IDs/classes might be:
   - Generated dynamically by JavaScript
   - Used in Django template loops (e.g., costs_m{{ forloop.counter }})
   - Part of third-party libraries

3. **Further investigation needed** for:
   - JavaScript-generated elements
   - Django template includes that weren't fully scanned
   - Conditional content based on project status or user permissions

4. **CSS that is definitely used** - Core layout, navigation, forms, tables, and dashboard elements are actively used throughout the application.