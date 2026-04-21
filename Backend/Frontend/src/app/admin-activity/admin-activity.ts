import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

interface Activity {
  id: number;
  actor: string;
  event: string;
  target: string;
  time: string;
  outcome: 'success' | 'failed' | 'warning';
  severity: 'low' | 'medium' | 'high';
  sourceIp: string;
}

@Component({
  selector: 'app-admin-activity',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin-activity.html',
  styleUrls: ['./admin-activity.css']
})
export class AdminActivityComponent implements OnInit {
  activities: Activity[] = [];
  filteredActivities: Activity[] = [];
  loading = true;
  selectedOutcome: 'all' | 'success' | 'failed' | 'warning' = 'all';
  selectedSeverity: 'all' | 'low' | 'medium' | 'high' = 'all';

  ngOnInit() {
    this.loadActivities();
  }

  loadActivities() {
    this.loading = true;

    this.activities = [
      { id: 101, actor: 'admin_core', event: 'ADMIN_LOGIN', target: 'Admin Console', time: '2026-04-21 09:14:22', outcome: 'success', severity: 'low', sourceIp: '10.24.8.15' },
      { id: 102, actor: 'unknown', event: 'ADMIN_LOGIN_FAILED', target: 'Admin Console', time: '2026-04-21 09:17:09', outcome: 'failed', severity: 'high', sourceIp: '185.244.25.93' },
      { id: 103, actor: 'ops_admin', event: 'POLICY_CHANGED', target: 'MFA Enforcement', time: '2026-04-21 09:42:18', outcome: 'warning', severity: 'medium', sourceIp: '10.24.8.11' },
      { id: 104, actor: 'sec_analyst_01', event: 'USER_SUSPENDED', target: 'jane_smith', time: '2026-04-21 10:01:40', outcome: 'success', severity: 'medium', sourceIp: '10.24.9.22' },
      { id: 105, actor: 'admin_core', event: 'BULK_EXPORT', target: 'Activity Logs', time: '2026-04-21 10:16:57', outcome: 'warning', severity: 'high', sourceIp: '10.24.8.15' }
    ];

    this.applyFilters();
    this.loading = false;
  }

  setOutcomeFilter(value: string) {
    this.selectedOutcome = value as typeof this.selectedOutcome;
    this.applyFilters();
  }

  setSeverityFilter(value: string) {
    this.selectedSeverity = value as typeof this.selectedSeverity;
    this.applyFilters();
  }

  applyFilters() {
    this.filteredActivities = this.activities.filter(item => {
      const matchesOutcome = this.selectedOutcome === 'all' || item.outcome === this.selectedOutcome;
      const matchesSeverity = this.selectedSeverity === 'all' || item.severity === this.selectedSeverity;
      return matchesOutcome && matchesSeverity;
    });
  }

  exportActivities() {
    alert('Export queued. Download link will appear in your notifications.');
  }
}
