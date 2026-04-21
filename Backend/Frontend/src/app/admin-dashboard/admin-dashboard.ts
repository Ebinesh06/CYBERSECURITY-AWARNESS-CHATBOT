import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

interface KpiCard {
  label: string;
  value: string;
  trend: string;
  state: 'good' | 'warn' | 'critical';
}

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="dashboard">
      <header class="hero">
        <div>
          <p class="eyebrow">Operations Overview</p>
          <h2>Platform Security Dashboard</h2>
          <p class="subtitle">Live posture view for access control, incidents, and compliance health.</p>
        </div>
        <div class="hero-actions">
          <button type="button">Export Report</button>
          <button type="button" class="secondary">View Policies</button>
        </div>
      </header>

      <div class="kpi-grid">
        <article *ngFor="let kpi of kpis" class="kpi-card" [class.warn]="kpi.state === 'warn'" [class.critical]="kpi.state === 'critical'">
          <p class="kpi-label">{{ kpi.label }}</p>
          <p class="kpi-value">{{ kpi.value }}</p>
          <p class="kpi-trend">{{ kpi.trend }}</p>
        </article>
      </div>

      <div class="panel-grid">
        <article class="panel">
          <h3>Threat Watchlist</h3>
          <ul>
            <li *ngFor="let threat of threatWatchlist">
              <span class="severity" [class.high]="threat.severity === 'High'" [class.medium]="threat.severity === 'Medium'">{{ threat.severity }}</span>
              <div>
                <p class="title">{{ threat.title }}</p>
                <p class="desc">{{ threat.summary }}</p>
              </div>
            </li>
          </ul>
        </article>

        <article class="panel">
          <h3>Compliance Checks</h3>
          <div class="checks">
            <div *ngFor="let check of complianceChecks" class="check-item">
              <div>
                <p class="title">{{ check.title }}</p>
                <p class="desc">{{ check.detail }}</p>
              </div>
              <span class="pill" [class.pass]="check.status === 'Pass'" [class.fail]="check.status === 'Action Required'">{{ check.status }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>
  `,
  styles: [`
    .dashboard { display: grid; gap: 16px; }
    .hero {
      display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;
      border: 1px solid rgba(133, 160, 247, 0.2);
      background: linear-gradient(130deg, rgba(27, 54, 122, 0.45), rgba(5, 100, 88, 0.2));
      border-radius: 14px; padding: 16px;
    }
    .eyebrow { margin: 0; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: #8da6dc; }
    h2 { margin: 4px 0; font-size: 24px; color: #f0f5ff; }
    .subtitle { margin: 0; color: #abbee7; }
    .hero-actions { display: flex; gap: 10px; }
    .hero-actions button {
      border: 1px solid rgba(126, 152, 236, 0.35); background: rgba(18, 35, 74, 0.8); color: #deebff;
      padding: 8px 12px; border-radius: 10px; font-weight: 600; cursor: pointer;
    }
    .hero-actions .secondary { background: rgba(14, 22, 40, 0.65); }

    .kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
    .kpi-card {
      border: 1px solid rgba(139, 163, 240, 0.18); border-radius: 12px; padding: 14px;
      background: rgba(15, 29, 60, 0.56);
    }
    .kpi-card.warn { border-color: rgba(255, 197, 80, 0.35); }
    .kpi-card.critical { border-color: rgba(255, 97, 125, 0.42); }
    .kpi-label { margin: 0; font-size: 12px; color: #90a6d3; }
    .kpi-value { margin: 8px 0 4px; font-size: 28px; font-weight: 700; color: #f2f7ff; }
    .kpi-trend { margin: 0; font-size: 12px; color: #8fc7a9; }

    .panel-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .panel {
      border: 1px solid rgba(130, 154, 239, 0.2); border-radius: 12px; padding: 14px;
      background: rgba(11, 21, 44, 0.68);
    }
    .panel h3 { margin: 0 0 12px; color: #ecf3ff; }

    ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
    li { display: flex; gap: 10px; align-items: flex-start; }
    .severity {
      min-width: 62px; text-align: center; font-size: 11px; font-weight: 700;
      padding: 4px 8px; border-radius: 999px; border: 1px solid rgba(146, 176, 248, 0.35);
      color: #cbd9fb; background: rgba(42, 78, 173, 0.45);
    }
    .severity.high { border-color: rgba(255, 105, 105, 0.35); color: #ffd0d0; background: rgba(145, 31, 52, 0.5); }
    .severity.medium { border-color: rgba(255, 205, 102, 0.35); color: #ffe2aa; background: rgba(138, 81, 4, 0.4); }
    .title { margin: 0; color: #e7efff; font-weight: 600; }
    .desc { margin: 2px 0 0; color: #9fb3df; font-size: 13px; }

    .checks { display: grid; gap: 10px; }
    .check-item {
      display: flex; justify-content: space-between; gap: 10px; align-items: flex-start;
      border: 1px solid rgba(123, 151, 232, 0.16); border-radius: 10px; padding: 10px;
      background: rgba(13, 25, 55, 0.5);
    }
    .pill {
      font-size: 11px; font-weight: 700; padding: 5px 8px; border-radius: 999px;
      border: 1px solid rgba(122, 149, 225, 0.3); color: #c5d8ff;
    }
    .pill.pass { border-color: rgba(62, 216, 169, 0.35); color: #bff8e3; }
    .pill.fail { border-color: rgba(255, 109, 109, 0.35); color: #ffd0d0; }

    @media (max-width: 1100px) {
      .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .panel-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 700px) {
      .hero { flex-direction: column; }
      .kpi-grid { grid-template-columns: 1fr; }
      h2 { font-size: 20px; }
    }
  `]
})
export class AdminDashboardComponent implements OnInit {
  kpis: KpiCard[] = [
    { label: 'Active Admin Sessions', value: '04', trend: 'Within policy threshold', state: 'good' },
    { label: 'Failed Login Attempts', value: '12', trend: '+3 in last 24h', state: 'warn' },
    { label: 'Open Security Alerts', value: '03', trend: '1 high priority', state: 'critical' },
    { label: 'Audit Coverage', value: '98.7%', trend: 'Above compliance target', state: 'good' }
  ];

  threatWatchlist = [
    { severity: 'High', title: 'Privileged brute-force attempts', summary: 'Repeated admin login failures detected from 2 source ranges.' },
    { severity: 'Medium', title: 'Policy drift risk', summary: 'One environment has MFA disabled for backup admin account.' },
    { severity: 'Medium', title: 'Suspicious export pattern', summary: 'Bulk activity exports triggered outside normal admin hours.' }
  ];

  complianceChecks = [
    { title: 'MFA Enforcement', detail: 'All admin accounts must require second factor.', status: 'Pass' },
    { title: 'Session Timeout Policy', detail: 'Configured value must be <= 30 minutes.', status: 'Pass' },
    { title: 'Password Rotation', detail: 'Privileged credentials older than 90 days.', status: 'Action Required' }
  ];

  constructor(private router: Router) {}

  ngOnInit() {
    if (localStorage.getItem('role') !== 'admin') {
      this.router.navigate(['/chat']);
    }
  }
}
