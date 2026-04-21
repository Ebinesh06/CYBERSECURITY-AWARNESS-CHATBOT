import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface AdminSecuritySettings {
  sessionTimeoutMinutes: number;
  maxLoginAttempts: number;
  lockoutDurationMinutes: number;
  passwordMinLength: number;
  requirePasswordSymbols: boolean;
  enforceMfaForAdmin: boolean;
  enableIpAllowlist: boolean;
  ipAllowlist: string;
  maintenanceMode: boolean;
  alertOnFailedLogins: boolean;
}

@Component({
  selector: 'app-admin-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-settings.html',
  styleUrls: ['./admin-settings.css']
})
export class AdminSettingsComponent implements OnInit {
  settings: AdminSecuritySettings = {
    sessionTimeoutMinutes: 15,
    maxLoginAttempts: 5,
    lockoutDurationMinutes: 30,
    passwordMinLength: 12,
    requirePasswordSymbols: true,
    enforceMfaForAdmin: true,
    enableIpAllowlist: false,
    ipAllowlist: '',
    maintenanceMode: false,
    alertOnFailedLogins: true
  };

  savedMessage = '';
  saveTimeout?: ReturnType<typeof setTimeout>;

  ngOnInit() {
    this.loadSettings();
  }

  loadSettings() {
    const raw = localStorage.getItem('adminSecuritySettings');
    if (!raw) return;

    try {
      const parsed = JSON.parse(raw);
      this.settings = { ...this.settings, ...parsed };
    } catch {
      // Keep defaults if parsing fails.
    }
  }

  saveSettings() {
    localStorage.setItem('adminSecuritySettings', JSON.stringify(this.settings));
    this.savedMessage = 'Security policy saved. Changes apply to new and active admin sessions.';

    if (this.saveTimeout) {
      clearTimeout(this.saveTimeout);
    }

    this.saveTimeout = setTimeout(() => {
      this.savedMessage = '';
    }, 3000);
  }

  resetToDefaults() {
    if (!confirm('Reset all admin security policies to recommended defaults?')) {
      return;
    }

    this.settings = {
      sessionTimeoutMinutes: 15,
      maxLoginAttempts: 5,
      lockoutDurationMinutes: 30,
      passwordMinLength: 12,
      requirePasswordSymbols: true,
      enforceMfaForAdmin: true,
      enableIpAllowlist: false,
      ipAllowlist: '',
      maintenanceMode: false,
      alertOnFailedLogins: true
    };

    this.saveSettings();
  }
}
