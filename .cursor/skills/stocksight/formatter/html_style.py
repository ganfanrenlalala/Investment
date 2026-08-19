# -*- coding: utf-8 -*-
"""CSS for self-contained StockSight HTML reports."""

def _style() -> str:
    return """
    :root {
      color-scheme: light;
      --bg: #f3f6fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #667085;
      --line: #d8e0ec;
      --danger: #c2412d;
      --accent: #2454d6;
      --shadow: 0 24px 70px rgba(23, 32, 51, 0.09);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
      line-height: 1.62;
    }
    main { width: min(1120px, calc(100% - 32px)); margin: 32px auto 56px; position: relative; }

    /* ---- Hero 头部动态渐变 ---- */
    @keyframes gradient-shift {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    header {
      border-radius: 8px;
      padding: 34px 38px;
      color: white;
      background-size: 200% 200%;
      animation: gradient-shift 8s ease infinite;
      box-shadow: var(--shadow);
    }
    h1 { margin: 0 0 12px; font-size: 34px; letter-spacing: 0; }
    h2 { margin: 0 0 18px; font-size: 21px; }
    h3 { margin: 0 0 8px; font-size: 15px; }
    .summary { width: min(760px, 100%); margin: 0; color: rgba(255,255,255,.86); }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      margin: 18px 0 0;
    }
    .metric, .panel, .chart-card, .risk-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .metric { padding: 12px; color: var(--ink); }
    .metric span { display: block; color: var(--muted); font-size: 12px; }
    .metric strong { display: block; margin-top: 4px; font-size: 17px; border-radius: 4px; padding: 0 2px; }
    .metric.danger strong { color: var(--danger); }

    /* ---- 涨跌幅热力色带 ---- */
    .metric.heat strong {
      display: inline-block;
      border-radius: 6px;
      padding: 2px 8px;
      margin-top: 4px;
    }

    /* ---- 面板入场动画 ---- */
    @keyframes fade-up {
      from { opacity: 0; transform: translateY(18px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .panel {
      margin-top: 18px;
      padding: 22px;
      box-shadow: 0 12px 32px rgba(23, 32, 51, 0.05);
      animation: fade-up 0.5s ease both;
    }
    .panel:nth-of-type(1) { animation-delay: 0s; }
    .panel:nth-of-type(2) { animation-delay: 0.08s; }
    .panel:nth-of-type(3) { animation-delay: 0.16s; }
    .panel:nth-of-type(4) { animation-delay: 0.24s; }
    .panel:nth-of-type(5) { animation-delay: 0.32s; }
    .panel:nth-of-type(6) { animation-delay: 0.40s; }
    .panel:nth-of-type(7) { animation-delay: 0.48s; }
    .panel:nth-of-type(8) { animation-delay: 0.56s; }
    .panel:nth-of-type(9) { animation-delay: 0.64s; }
    .panel:nth-of-type(10) { animation-delay: 0.72s; }
    @media (prefers-reduced-motion: reduce) {
      .panel { animation: none; }
      header { animation: none; }
    }

    .chart-grid {
      display: grid;
      grid-template-columns: 260px 1fr;
      gap: 16px;
      align-items: stretch;
    }
    .chart-grid.enriched { margin-top: 16px; }
    .chart-card { padding: 18px; }
    .pie {
      width: 164px;
      aspect-ratio: 1;
      border-radius: 50%;
      margin: 14px auto;
      display: grid;
      place-items: center;
      box-shadow: inset 0 0 0 18px rgba(255,255,255,.82);
    }
    .pie span { font-size: 28px; font-weight: 800; }
    .bar-row {
      display: grid;
      grid-template-columns: minmax(90px, 170px) 1fr 42px minmax(84px, auto);
      gap: 10px;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid #edf1f7;
    }
    .bar-row:last-child { border-bottom: 0; }
    .bar-row b {
      display: inline-block;
      width: 9px;
      height: 9px;
      border-radius: 50%;
      margin-right: 8px;
    }
    .bar-track { height: 11px; border-radius: 99px; background: #edf1f7; overflow: hidden; }
    .bar-track i { display: block; height: 100%; border-radius: inherit; }
    .bar-row em { color: var(--muted); font-style: normal; font-size: 13px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 11px 12px; border-bottom: 1px solid var(--line); text-align: left; }
    th { background: #f0f4fa; color: #344054; }
    tr:last-child td { border-bottom: 0; }
    kbd {
      display: inline-block;
      padding: 2px 7px;
      border: 1px solid #cfd7e6;
      border-bottom-width: 2px;
      border-radius: 6px;
      background: #f8fafc;
      color: #253858;
      font-family: inherit;
      font-size: 13px;
      font-weight: 700;
    }
    .risk-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
    .risk-card { padding: 14px; }
    .empty-state { padding: 16px; border-radius: 8px; background: #f8fafc; color: var(--muted); }
    .section-brief {
      margin: -4px 0 14px;
      color: #344054;
      font-size: 14px;
      background: #f8fafc;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
    }
    .risk-insight-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .risk-insight-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 13px 14px;
      background: #ffffff;
    }
    .risk-insight-card span {
      display: block;
      color: var(--muted);
      font-size: 12px;
    }
    .risk-insight-card strong {
      display: block;
      margin-top: 4px;
      font-size: 21px;
      color: var(--ink);
    }
    .risk-insight-card em {
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 12px;
      font-style: normal;
    }
    .anomaly-breakdown-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
    }
    .anomaly-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #ffffff;
    }
    .anomaly-card-head,
    .anomaly-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }
    .anomaly-card-head span {
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }
    .anomaly-card-head strong {
      font-size: 24px;
      color: var(--ink);
    }
    .anomaly-bar {
      height: 8px;
      border-radius: 999px;
      background: #edf1f7;
      overflow: hidden;
      margin: 10px 0 8px;
    }
    .anomaly-bar i {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: #2563eb;
    }
    .anomaly-card.low .anomaly-bar i { background: #94a3b8; }
    .anomaly-card.medium .anomaly-bar i { background: #d79b2b; }
    .anomaly-card.high .anomaly-bar i { background: #d36b23; }
    .anomaly-meta b {
      color: var(--ink);
      font-size: 13px;
    }
    .anomaly-meta em {
      color: var(--muted);
      font-size: 12px;
      font-style: normal;
    }
    .anomaly-card p {
      margin: 9px 0 0;
      color: #475569;
      font-size: 12px;
      line-height: 1.55;
    }
    .risk-explain-list {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 10px;
      margin-top: 14px;
    }
    .risk-explain-item {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
      background: #fffaf7;
    }
    .risk-explain-item strong { margin-right: 8px; }
    .risk-explain-item span {
      color: var(--danger);
      font-size: 12px;
      font-weight: 800;
    }
    .risk-explain-item p {
      margin: 6px 0 0;
      color: #475569;
      font-size: 13px;
    }
    .signal-detail-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
      margin-top: 14px;
    }
    .signal-detail-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #ffffff;
    }
    .signal-detail-head {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }
    .signal-detail-head span {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex-shrink: 0;
    }
    .signal-detail-head strong { flex: 1; }
    .signal-detail-card p {
      margin: 0 0 10px;
      color: #475569;
      font-size: 13px;
    }
    .signal-detail-card dl {
      display: grid;
      gap: 7px;
      margin: 0;
    }
    .signal-detail-card dl div {
      display: grid;
      grid-template-columns: 72px 1fr;
      gap: 8px;
      align-items: start;
    }
    .signal-detail-card dt {
      color: var(--muted);
      font-size: 12px;
    }
    .signal-detail-card dd {
      margin: 0;
      color: var(--ink);
      font-size: 12px;
    }
    .muted, footer { color: var(--muted); font-size: 13px; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    footer { margin-top: 14px; padding: 0 4px; }

    /* ---- 新风险仪表盘 ---- */
    .risk-dashboard-shell {
      max-width: 940px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: minmax(420px, 1fr) 220px;
      gap: 26px;
      align-items: center;
    }
    .gauge-stage {
      display: grid;
      place-items: center;
    }
    .new-gauge-svg {
      width: 100%;
      max-width: 640px;
      height: auto;
      overflow: visible;
    }
    .gauge-tick {
      font-size: 16px;
      font-weight: 700;
      fill: #475569;
    }
    .gauge-label {
      font-size: 14px;
      font-weight: 700;
      fill: #667085;
    }
    .gauge-score-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px 18px 16px;
      background: #ffffff;
      box-shadow: 0 12px 32px rgba(23, 32, 51, 0.05);
    }
    .gauge-score-card span {
      display: block;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }
    .gauge-score-card strong {
      display: block;
      margin-top: 4px;
      font-size: 58px;
      line-height: 1;
      font-weight: 900;
    }
    .gauge-score-card b {
      display: block;
      margin-top: 4px;
      font-size: 22px;
    }
    .gauge-score-card em {
      display: inline-block;
      margin-top: 12px;
      padding: 4px 10px;
      border-radius: 99px;
      background: #fff4e6;
      color: #d36b23;
      font-size: 13px;
      font-style: normal;
      font-weight: 800;
    }
    .gauge-score-card p {
      margin: 12px 0 0;
      color: var(--muted);
      font-size: 12px;
    }
    .gauge-legend-pro {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 14px;
      margin-top: 2px;
      grid-column: 1 / -1;
    }
    .gauge-legend-item {
      display: flex;
      align-items: center;
      gap: 7px;
      font-size: 13px;
      color: var(--ink);
    }
    .gauge-legend-item span {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      flex-shrink: 0;
    }
    .gauge-legend-item strong {
      font-size: 13px;
      font-weight: 800;
      white-space: nowrap;
    }
    .gauge-legend-item em {
      color: var(--muted);
      font-style: normal;
      white-space: nowrap;
    }

    /* ---- 新六边形雷达 ---- */
    .radar-dashboard {
      display: grid;
      grid-template-columns: minmax(360px, 1fr) minmax(360px, 1fr);
      gap: 24px;
      align-items: center;
    }
    .radar-stage {
      min-height: 420px;
      display: grid;
      place-items: center;
    }
    .new-radar-svg {
      width: 100%;
      max-width: 520px;
      height: auto;
      flex-shrink: 0;
    }
    .radar-scale {
      font-size: 10px;
      fill: #94a3b8;
      font-weight: 600;
    }
    .radar-axis-label {
      font-size: 14px;
      fill: #172033;
      font-weight: 800;
    }
    .signal-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .signal-row {
      display: grid;
      grid-template-columns: 36px minmax(80px, 120px) 1fr auto;
      gap: 12px;
      align-items: center;
      padding: 13px 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      box-shadow: 0 8px 22px rgba(23, 32, 51, 0.04);
    }
    .signal-icon {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      color: white;
      font-weight: 800;
      font-size: 13px;
    }
    .signal-0 { background: #2563eb; }
    .signal-1 { background: #7c3aed; }
    .signal-2 { background: #f97316; }
    .signal-3 { background: #0f766e; }
    .signal-4 { background: #ef4444; }
    .signal-5 { background: #64748b; }
    .signal-row strong { font-size: 14px; }
    .signal-row em {
      color: var(--muted);
      font-size: 13px;
      font-style: normal;
    }
    .signal-row b {
      padding: 4px 12px;
      border-radius: 99px;
      font-size: 12px;
      white-space: nowrap;
    }
    .signal-row b.bull { background: #e7f8ee; color: #16794c; }
    .signal-row b.bear { background: #fdeaea; color: #c2412d; }
    .signal-row b.watch { background: #fff4db; color: #b7791f; }
    .signal-row b.neutral { background: #f1f5f9; color: #667085; }

    /* ---- 操作建议决策卡 ---- */
    .decision-card {
      display: grid;
      grid-template-columns: 1fr auto 1fr auto 1fr;
      align-items: center;
      gap: 0;
      background: #f8fafc;
      border-radius: 12px;
      padding: 20px 16px;
      border: 1px solid var(--line);
    }
    .dc-col {
      text-align: center;
      padding: 8px 12px;
    }
    .dc-loss { border-right: none; }
    .dc-target { border-left: none; }
    .dc-current { padding: 8px 20px; }
    .dc-divider {
      width: 1px;
      height: 60px;
      background: var(--line);
    }
    .dc-label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
    .dc-price { display: block; font-size: 20px; font-weight: 800; }
    .dc-price-main { font-size: 26px; color: var(--accent); }
    .dc-note { display: block; font-size: 11px; color: var(--muted); margin-top: 2px; }
    .dc-loss .dc-price { color: var(--danger); }
    .dc-target .dc-price { color: #16794c; }
    .dc-arrow { font-size: 14px; margin-bottom: 4px; }
    .dc-arrow-down { color: var(--danger); }
    .dc-arrow-up { color: #16794c; }
    .dc-action-badge {
      display: inline-block;
      padding: 3px 14px;
      border-radius: 99px;
      font-size: 13px;
      font-weight: 700;
      color: white;
      margin-bottom: 6px;
    }
    .dc-action-badge.healthy { background: #16794c; }
    .dc-action-badge.watch { background: #d79b2b; }
    .dc-action-badge.caution { background: #d36b23; }
    .dc-action-badge.danger { background: #c2412d; }
    .dc-strategy-details {
      margin-top: 12px;
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #ffffff;
    }
    .dc-strategy-details p {
      margin: 0 0 10px;
      color: var(--text);
      font-weight: 700;
    }
    .dc-strategy-details ul {
      margin: 0 0 12px 18px;
      padding: 0;
      color: var(--muted);
      font-size: 13px;
    }
    .dc-strategy-details li { margin: 4px 0; }
    .strategy-performance {
      margin-top: 18px;
      padding: 16px;
      border: 1px solid #dbe6f4;
      border-radius: 14px;
      background: #f8fbff;
    }
    .strategy-performance h3 { margin: 0 0 12px; font-size: 16px; }
    .strategy-performance-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .strategy-performance-grid div {
      padding: 10px;
      border-radius: 10px;
      background: white;
      border: 1px solid #e7edf5;
    }
    .strategy-performance-grid span {
      display: block;
      color: #6b7280;
      font-size: 12px;
      margin-bottom: 4px;
    }
    .strategy-performance-grid strong { font-size: 17px; color: #172033; }
    .trade-plan-details {
      margin-top: 18px;
      padding: 16px;
      border: 1px solid #d9e5dc;
      border-radius: 14px;
      background: #f7fbf8;
    }
    .trade-plan-details h3 { margin: 0 0 10px; font-size: 16px; }
    .trade-plan-details dl {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px 14px;
      margin: 12px 0;
    }
    .trade-plan-details dl div {
      padding: 9px 10px;
      border: 1px solid #e1ebe4;
      border-radius: 9px;
      background: white;
    }
    .trade-plan-details dt { color: #6b7280; font-size: 12px; }
    .trade-plan-details dd { margin: 3px 0 0; font-weight: 700; color: #172033; }
    .trade-lifecycle-details {
      margin-top: 18px;
      padding: 16px;
      border: 1px solid #d8def3;
      border-radius: 14px;
      background: #f7f8fe;
    }
    .trade-lifecycle-details h3 { margin: 0 0 12px; font-size: 16px; }
    .lifecycle-steps {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 14px;
    }
    .lifecycle-step {
      padding: 9px 6px;
      border: 1px solid #e2e5ef;
      border-radius: 10px;
      background: white;
      color: #98a0b3;
      text-align: center;
    }
    .lifecycle-step span {
      display: block;
      width: 22px;
      height: 22px;
      margin: 0 auto 5px;
      border-radius: 50%;
      background: #eef0f6;
      font-size: 12px;
      line-height: 22px;
    }
    .lifecycle-step strong { font-size: 12px; }
    .lifecycle-step.done {
      border-color: #b9ddca;
      color: #16794c;
      background: #f4fbf7;
    }
    .lifecycle-step.done span { color: white; background: #16794c; }
    .lifecycle-step.active {
      border-color: #9fb4ef;
      color: #2454d6;
      background: #f2f5ff;
      box-shadow: inset 0 0 0 1px #c8d4f8;
    }
    .lifecycle-step.active span { color: white; background: #2454d6; }
    .trade-lifecycle-details dl {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px 14px;
      margin: 0 0 12px;
    }
    .trade-lifecycle-details dl div {
      padding: 9px 10px;
      border: 1px solid #e3e6f1;
      border-radius: 9px;
      background: white;
    }
    .trade-lifecycle-details dt { color: #6b7280; font-size: 12px; }
    .trade-lifecycle-details dd { margin: 3px 0 0; font-weight: 700; color: #172033; }
    .lifecycle-events {
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .lifecycle-events li {
      display: grid;
      grid-template-columns: 145px 120px 1fr;
      gap: 8px;
      padding: 7px 0;
      border-top: 1px solid #e3e6f1;
      font-size: 12px;
    }
    .lifecycle-events span, .lifecycle-events em { color: #6b7280; font-style: normal; }
    .dc-strategy-details dl {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin: 0;
    }
    .dc-strategy-details dl div {
      padding: 10px;
      background: #f8fafc;
      border-radius: 8px;
    }
    .dc-strategy-details dt {
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      margin-bottom: 4px;
    }
    .dc-strategy-details dd {
      margin: 0;
      color: var(--text);
      font-size: 13px;
      line-height: 1.55;
    }
    .strategy-split {
      margin-top: 18px;
      padding-top: 16px;
      border-top: 1px solid var(--line);
    }
    .strategy-split h3 {
      margin: 0 0 10px;
      font-size: 17px;
      color: var(--text);
    }
    .strategy-split-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 12px;
    }
    .strategy-split-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fff;
    }
    .strategy-split-card h4 {
      margin: 0 0 6px;
      font-size: 15px;
      color: var(--text);
    }
    .strategy-split-meta {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin: 10px 0;
      font-size: 12px;
      color: var(--muted);
    }
    .strategy-split-meta strong {
      display: block;
      color: var(--text);
      margin-top: 2px;
    }
    .strategy-split-card ul {
      margin: 8px 0 0 18px;
      padding: 0;
    }
    .dc-disclaimer { margin-top: 12px; text-align: center; }

    /* ---- 最终判断 ---- */
    .judgment-panel {
      border-left: 4px solid var(--accent);
      background:
        radial-gradient(circle at 16% 0%, rgba(47,111,237,.10), transparent 32%),
        var(--panel);
    }
    .judgment-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      margin-bottom: 16px;
    }
    .judgment-head h2 { margin: 2px 0 0; }
    .eyebrow {
      display: inline-block;
      color: var(--muted);
      font-size: 11px;
      font-weight: 800;
      letter-spacing: .08em;
    }
    .judgment-badge {
      padding: 7px 14px;
      border-radius: 999px;
      color: #fff;
      font-size: 13px;
      white-space: nowrap;
      box-shadow: 0 8px 18px rgba(23,32,51,.12);
    }
    .judgment-badge.healthy { background: #16794c; }
    .judgment-badge.watch { background: #d79b2b; }
    .judgment-badge.warning { background: #d36b23; }
    .judgment-badge.danger { background: #c2412d; }
    .judgment-grid {
      display: grid;
      grid-template-columns: minmax(160px, .8fr) minmax(220px, 1.3fr) minmax(220px, 1.4fr);
      gap: 12px;
    }
    .judgment-grid article {
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(255,255,255,.78);
    }
    .judgment-grid span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }
    .judgment-grid strong {
      display: block;
      color: var(--ink);
      line-height: 1.55;
    }
    .judgment-grid p {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.6;
    }

    /* ---- 信号雷达图 ---- */
    .radar-wrapper {
      display: flex;
      align-items: center;
      gap: 24px;
    }
    .radar-svg {
      width: 200px;
      height: 200px;
      flex-shrink: 0;
    }
    .radar-grid {
      fill: none;
      stroke: var(--line);
      stroke-width: 0.5;
    }
    .radar-axis {
      stroke: var(--line);
      stroke-width: 0.3;
    }
    .radar-value {
      fill: rgba(36, 84, 214, 0.15);
      stroke: #2454d6;
      stroke-width: 1;
    }
    .radar-dot {
      fill: #2454d6;
    }
    .radar-label {
      font-size: 5px;
      fill: var(--muted);
      dominant-baseline: middle;
    }
    .radar-legend {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .rl-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
    }
    .rl-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    /* ---- 侧边导航 ---- */
    .side-nav {
      position: fixed;
      left: 12px;
      top: 50%;
      transform: translateY(-50%);
      display: flex;
      flex-direction: column;
      gap: 6px;
      z-index: 100;
    }
    .nav-item {
      display: grid;
      place-items: center;
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: 0 2px 8px rgba(23,32,51,.06);
      font-size: 14px;
      text-decoration: none;
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .nav-item:hover {
      transform: scale(1.12);
      box-shadow: 0 4px 12px rgba(23,32,51,.12);
      text-decoration: none;
    }

    /* ---- 品牌水印 ---- */
    main::after {
      content: "StockSight";
      position: fixed;
      bottom: 18px;
      right: 24px;
      font-size: 48px;
      font-weight: 900;
      color: rgba(23, 32, 51, 0.03);
      letter-spacing: -1px;
      pointer-events: none;
      z-index: 0;
    }
    footer {
      position: relative;
      z-index: 1;
    }
    .footer-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .footer-version { font-size: 11px; color: var(--muted); opacity: 0.6; }

    /* ---- 技术指标面板 ---- */
    .technical-grid {
      display: grid;
      grid-template-columns: minmax(0, 2fr) minmax(220px, 1fr);
      gap: 18px;
      align-items: stretch;
    }
    .macd-chart-container {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: linear-gradient(180deg, #fff 0%, #f8fafc 100%);
      padding: 10px;
    }
    .macd-svg {
      display: block;
      width: 100%;
      height: auto;
    }
    .macd-date-label,
    .macd-legend {
      fill: var(--muted);
      font-size: 10px;
    }
    .rsi-panel {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: linear-gradient(180deg, #fff 0%, #f8fafc 100%);
      padding: 18px;
      min-height: 170px;
    }
    .rsi-panel h3 {
      margin: 0 0 16px;
      color: var(--muted);
      font-size: 13px;
      letter-spacing: .04em;
    }
    .rsi-panel strong {
      display: block;
      font-size: 38px;
      line-height: 1;
      color: var(--ink);
    }
    .rsi-panel p {
      margin: 8px 0 18px;
      color: var(--muted);
      font-weight: 700;
    }
    .rsi-panel.bearish strong { color: #c2412d; }
    .rsi-panel.watch strong { color: #d79b2b; }
    .rsi-track {
      position: relative;
      display: grid;
      grid-template-columns: 30fr 40fr 30fr;
      height: 12px;
      border-radius: 999px;
      overflow: visible;
      background: #edf1f7;
    }
    .rsi-zone { min-width: 0; }
    .rsi-zone.low { background: #f7d88b; border-radius: 999px 0 0 999px; }
    .rsi-zone.mid { background: #dce7f5; }
    .rsi-zone.high { background: #f0a199; border-radius: 0 999px 999px 0; }
    .rsi-track i {
      position: absolute;
      top: 50%;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: var(--ink);
      border: 3px solid white;
      box-shadow: 0 2px 8px rgba(23,32,51,.25);
      transform: translate(-50%, -50%);
    }
    .rsi-labels {
      display: flex;
      justify-content: space-between;
      margin-top: 10px;
      font-size: 11px;
      color: var(--muted);
    }
    .technical-signals {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-top: 16px;
    }
    .technical-signal {
      border: 1px solid var(--line);
      border-left: 4px solid #94a3b8;
      border-radius: 10px;
      background: #fff;
      padding: 12px 14px;
    }
    .technical-signal.bullish { border-left-color: #16a34a; }
    .technical-signal.bearish { border-left-color: #c2412d; }
    .technical-signal span,
    .technical-signal em {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-style: normal;
    }
    .technical-signal strong {
      display: block;
      margin: 5px 0;
      color: var(--ink);
      font-size: 14px;
      line-height: 1.5;
    }

    /* ---- 价格区间卡片 ---- */
    .price-range-card { padding: 8px 0; }
    .range-labels {
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 8px;
    }
    .range-track {
      position: relative;
      height: 28px;
      background: linear-gradient(90deg, #e74c3c 0%, #edf1f7 40%, #edf1f7 60%, #27ae60 100%);
      border-radius: 14px;
      margin: 0 4px;
    }
    .range-marker {
      position: absolute;
      top: 50%;
      transform: translate(-50%, -50%);
      display: flex;
      flex-direction: column;
      align-items: center;
      z-index: 2;
    }
    .marker-dot {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      border: 2px solid white;
      box-shadow: 0 1px 4px rgba(0,0,0,.2);
    }
    .range-marker.prev .marker-dot { background: #667085; }
    .range-marker.open .marker-dot { background: #2454d6; }
    .range-marker.current .marker-dot { background: var(--ink); width: 16px; height: 16px; border-width: 3px; }
    .marker-label {
      position: absolute;
      top: 22px;
      white-space: nowrap;
      font-size: 11px;
      color: var(--ink);
      font-weight: 600;
      background: white;
      padding: 1px 5px;
      border-radius: 4px;
      border: 1px solid var(--line);
    }
    .range-meta {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: var(--muted);
      margin-top: 28px;
    }

    /* ---- 量价关系模块 ---- */
    .vp-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .vp-card {
      background: #f8fafc;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }
    .vp-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
    }
    .vp-header h3 { margin: 0; font-size: 15px; }
    .vp-badge {
      display: inline-block;
      padding: 2px 10px;
      border-radius: 99px;
      font-size: 12px;
      font-weight: 700;
      color: white;
    }
    .vp-badge.healthy { background: #16794c; }
    .vp-badge.caution { background: #d36b23; }
    .vp-badge.danger { background: #c2412d; }
    .vp-badge.neutral { background: #667085; }
    .vp-badge.watch { background: #d79b2b; }
    .vp-card p { margin: 0 0 12px; color: var(--muted); font-size: 13px; }
    .vp-bars { display: flex; flex-direction: column; gap: 8px; }
    .vp-bar-row {
      display: grid;
      grid-template-columns: 48px 1fr 48px;
      gap: 8px;
      align-items: center;
      font-size: 13px;
    }
    .vp-bar-row span { color: var(--muted); }
    .vp-bar-track {
      height: 8px;
      border-radius: 99px;
      background: #edf1f7;
      overflow: hidden;
    }
    .vp-bar-track i { display: block; height: 100%; border-radius: inherit; }
    .vp-bar-row strong { text-align: right; font-size: 13px; }
    .vp-dimension-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .vp-dim {
      background: white;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      text-align: center;
    }
    .dim-label { display: block; font-size: 11px; color: var(--muted); }
    .dim-value { display: block; font-size: 14px; margin-top: 2px; }

    /* ---- 资讯时间线 ---- */
    .timeline {
      position: relative;
      padding-left: 28px;
    }
    .timeline::before {
      content: "";
      position: absolute;
      left: 8px;
      top: 4px;
      bottom: 4px;
      width: 2px;
      background: var(--line);
      border-radius: 1px;
    }
    .timeline-item {
      position: relative;
      padding-bottom: 18px;
    }
    .timeline-item:last-child { padding-bottom: 0; }
    .timeline-dot {
      position: absolute;
      left: -24px;
      top: 4px;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--accent);
      border: 2px solid white;
      box-shadow: 0 0 0 2px var(--line);
    }
    .timeline-content h3 { margin: 0 0 4px; font-size: 14px; }
    .timeline-meta {
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 4px;
    }
    .timeline-meta span + span::before { content: "·"; margin: 0 4px; }
    .timeline-content p { margin: 4px 0 0; font-size: 13px; color: var(--muted); }

    /* ---- 数据完整性面板 ---- */
    .quality-panel { border-left: 4px solid var(--accent); }
    .qi-grid {
      display: grid;
      grid-template-columns: 140px 1fr;
      gap: 20px;
      align-items: start;
    }
    .qi-ring { text-align: center; }
    .qi-ring-inner {
      width: 100px;
      aspect-ratio: 1;
      border-radius: 50%;
      margin: 0 auto 8px;
      display: grid;
      place-items: center;
      box-shadow: inset 0 0 0 12px rgba(255,255,255,.88);
    }
    .qi-ring-inner span { font-size: 20px; font-weight: 800; }
    .qi-items {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
      gap: 6px;
    }
    .qi-item {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 8px;
      border-radius: 6px;
      font-size: 13px;
      background: #f8fafc;
      border: 1px solid var(--line);
    }
    .qi-item.ok { border-color: #c6e4c6; }
    .qi-item.unavailable { border-color: #f5d6a8; }
    .qi-item.missing { border-color: #f0b8b8; }
    .qi-icon {
      width: 18px;
      height: 18px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      font-size: 10px;
      font-weight: 700;
      color: white;
      flex-shrink: 0;
    }
    .qi-item.ok .qi-icon { background: #16794c; }
    .qi-item.unavailable .qi-icon { background: #d79b2b; }
    .qi-item.missing .qi-icon { background: #c2412d; }
    .qi-label { flex: 1; }
    .qi-status { color: var(--muted); font-size: 12px; }
    .qi-notes { grid-column: 1 / -1; margin-top: 8px; }
    .qi-notes p { margin: 4px 0; font-size: 13px; color: var(--muted); }
    .trust-block {
      grid-column: 1 / -1;
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid var(--line);
    }
    .trust-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 10px;
    }
    .trust-head h3 { margin: 0; font-size: 15px; }
    .trust-head strong {
      padding: 4px 10px;
      border-radius: 999px;
      background: #edf4ff;
      color: var(--accent);
      font-size: 12px;
    }
    .trust-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 8px;
    }
    .trust-item {
      padding: 10px;
      border-radius: 10px;
      border: 1px solid var(--line);
      background: #fff;
    }
    .trust-item span,
    .trust-item em,
    .trust-item p {
      display: block;
      font-style: normal;
      font-size: 12px;
      color: var(--muted);
    }
    .trust-item strong {
      display: block;
      margin: 4px 0 3px;
      color: var(--ink);
    }
    .trust-item p { margin: 4px 0 0; line-height: 1.45; }
    .trust-item.ok { border-color: #c6e4c6; }
    .trust-item.computed { border-color: #bcd4ff; }
    .trust-item.derived { border-color: #f5d6a8; }
    .trust-item.unavailable { border-color: #f0b8b8; }

    /* ---- 响应式 ---- */
    @media (max-width: 820px) {
      main { width: 100%; margin: 0; }
      header { border-radius: 0; animation: none; padding: 26px 18px; }
      h1 { font-size: 26px; }
      .metric-grid, .chart-grid { grid-template-columns: 1fr; }
      .judgment-head { flex-direction: column; }
      .judgment-grid { grid-template-columns: 1fr; }
      .risk-insight-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .panel { border-radius: 0; margin-top: 12px; }
      .bar-row { grid-template-columns: 1fr; gap: 6px; }
      table { display: block; overflow-x: auto; }
      .vp-grid { grid-template-columns: 1fr; }
      .qi-grid { grid-template-columns: 1fr; }
      .qi-ring-inner { margin: 0 auto; }
      .side-nav { display: none; }
      .decision-card { grid-template-columns: 1fr; gap: 8px; }
      .dc-divider { width: 60px; height: 1px; margin: 0 auto; }
      .dc-strategy-details dl { grid-template-columns: 1fr; }
      .strategy-performance-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .trade-plan-details dl { grid-template-columns: 1fr; }
      .lifecycle-steps { grid-template-columns: repeat(5, minmax(52px, 1fr)); overflow-x: auto; }
      .trade-lifecycle-details dl { grid-template-columns: 1fr; }
      .lifecycle-events li { grid-template-columns: 1fr; gap: 2px; }
      .radar-dashboard { grid-template-columns: 1fr; }
      .radar-stage { min-height: auto; }
      .signal-row { grid-template-columns: 32px 1fr; }
      .signal-row em, .signal-row b { grid-column: 2; }
      .risk-dashboard-shell { grid-template-columns: 1fr; }
      .gauge-legend-pro { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }

    /* ---- 打印样式 ---- */
    @page {
      size: A4;
      margin: 10mm;
    }
    @media print {
      html, body {
        width: auto;
        min-width: 0;
        background: white;
        color: #172033;
        font-size: 10pt;
        line-height: 1.42;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }
      * {
        animation: none !important;
        transition: none !important;
        box-shadow: none !important;
        text-shadow: none !important;
      }
      main {
        width: 190mm;
        max-width: 190mm;
        margin: 0 auto;
      }
      main::after,
      .side-nav {
        display: none !important;
      }
      header {
        background: #172033 !important;
        border-radius: 0;
        padding: 14mm 10mm 10mm;
        break-inside: avoid;
        page-break-inside: avoid;
      }
      h1 { font-size: 22pt; }
      h2 { font-size: 15pt; margin-bottom: 8mm; }
      h3 { font-size: 11pt; }
      .panel {
        margin-top: 8mm;
        padding: 8mm;
        border: 1px solid #d8e0ec;
        border-radius: 0;
        break-inside: avoid;
        page-break-inside: avoid;
      }
      .metric-grid {
        grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
        gap: 4mm;
      }
      .metric,
      .chart-card,
      .risk-card,
      .vp-card,
      .risk-insight-card,
      .signal-detail-card,
      .signal-row,
      .qi-item {
        border: 1px solid #d8e0ec;
        background: #fff;
      }
      .chart-grid,
      .chart-grid.enriched {
        grid-template-columns: 42mm 1fr !important;
        gap: 6mm;
      }
      .risk-dashboard-shell {
        grid-template-columns: 1fr 44mm !important;
        gap: 6mm;
        max-width: none;
      }
      .new-gauge-svg {
        max-width: 118mm;
        width: 118mm;
      }
      .gauge-score-card {
        padding: 5mm;
      }
      .gauge-score-card strong {
        font-size: 32pt;
      }
      .gauge-score-card b {
        font-size: 13pt;
      }
      .gauge-legend-pro {
        grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
        gap: 3mm;
      }
      .gauge-legend-item {
        font-size: 8pt;
      }
      .radar-dashboard {
        grid-template-columns: 78mm 1fr !important;
        gap: 8mm;
        align-items: center;
      }
      .radar-stage {
        min-height: 0;
      }
      .new-radar-svg {
        width: 78mm;
        max-width: 78mm;
      }
      .signal-row {
        grid-template-columns: 8mm 24mm 1fr 16mm !important;
        gap: 3mm;
        padding: 3mm;
      }
      .signal-row em,
      .signal-row b {
        grid-column: auto !important;
      }
      .risk-insight-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
        gap: 3mm;
      }
      .signal-detail-grid,
      .risk-explain-list,
      .risk-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 4mm;
      }
      .vp-grid,
      .qi-grid {
        grid-template-columns: 1fr 1fr !important;
        gap: 5mm;
      }
      .decision-card {
        grid-template-columns: 1fr 1px 1fr 1px 1fr !important;
      }
      .dc-divider {
        width: 1px !important;
        height: 20mm !important;
      }
      table {
        page-break-inside: auto;
        font-size: 9pt;
      }
      tr { page-break-inside: avoid; }
      .bar-track { background: #edf1f7; }
      th { background: #f0f4fa; }
      .empty-state { background: #f8fafc; }
      a { color: #1a1a1a; text-decoration: underline; }
      footer { margin-top: 8px; }
    }

    /* === Trend Summary Cards === */
    .trend-summary {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 12px 0;
    }
    .trend-card {
      flex: 1 1 280px;
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 12px 14px;
      border-radius: 10px;
      background: #f8faff;
      border: 1px solid #e0e6f0;
    }
    .trend-card.bullish { border-left: 3px solid #16794c; background: #f0faf4; }
    .trend-card.bearish { border-left: 3px solid #c2412d; background: #fef4f2; }
    .trend-card.watch   { border-left: 3px solid #d79b2b; background: #fffbf0; }
    .trend-card.neutral { border-left: 3px solid #94a3b8; background: #f8fafc; }
    .trend-icon {
      font-size: 20px;
      line-height: 1.4;
      flex-shrink: 0;
      width: 28px;
      text-align: center;
    }
    .trend-body { flex: 1; min-width: 0; }
    .trend-label {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--muted);
      display: block;
      margin-bottom: 2px;
    }
    .trend-body strong {
      display: block;
      font-size: 13px;
      line-height: 1.4;
      margin-bottom: 2px;
    }
    .trend-body em {
      display: block;
      font-size: 12px;
      color: var(--muted);
      font-style: normal;
    }

    /* === Hero Judgment Banner === */
    .judgment-hero {
      margin: 18px 0 6px;
      border-radius: 14px;
      padding: 22px 26px;
      box-shadow: 0 8px 24px rgba(23, 32, 51, 0.06);
      animation: fade-up 0.45s ease both;
    }
    .judgment-hero-inner {
      display: flex;
      align-items: flex-start;
      gap: 18px;
    }
    .judgment-status-badge {
      flex-shrink: 0;
      min-width: 110px;
      text-align: center;
      padding: 13px 16px;
      border-radius: 12px;
      font-weight: 700;
      font-size: 16px;
      line-height: 1.3;
    }
    .judgment-status-badge.danger {
      background: #fecaca;
      color: #991b1b;
    }
    .judgment-status-badge.warning {
      background: #fed7aa;
      color: #92400e;
    }
    .judgment-status-badge.watch {
      background: #bae6fd;
      color: #1e40af;
    }
    .judgment-status-badge.healthy {
      background: #bbf7d0;
      color: #166534;
    }
    .judgment-hero-body {
      flex: 1;
      min-width: 0;
    }
    .judgment-risk-line {
      font-size: 14px;
      font-weight: 600;
      color: var(--ink);
      margin: 0 0 4px;
      line-height: 1.45;
    }
    .judgment-trend-line {
      font-size: 12.5px;
      color: var(--muted);
      margin: 0;
      line-height: 1.4;
    }
    .judgment-hero-action {
      flex-shrink: 0;
      width: 260px;
      border-left: 1px solid var(--line);
      padding-left: 18px;
    }
    .judgment-hero-action span {
      display: block;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--muted);
      margin-bottom: 4px;
    }
    .judgment-hero-action p {
      font-size: 12.5px;
      color: var(--ink);
      margin: 0;
      line-height: 1.45;
    }

    /* Compact variant for narrow */
    @media (max-width: 760px) {
      .judgment-hero-inner {
        flex-direction: column;
        gap: 12px;
      }
      .judgment-hero-action {
        width: 100%;
        border-left: none;
        border-top: 1px solid var(--line);
        padding-left: 0;
        padding-top: 12px;
      }
      .judgment-status-badge {
        min-width: auto;
        align-self: flex-start;
      }
    }

""


# =============================================================================
# 主渲染入口
    """
