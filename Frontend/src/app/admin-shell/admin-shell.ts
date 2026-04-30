import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { Subscription, filter } from 'rxjs';

@Component({
  selector: 'app-admin-shell',
  standalone: true,
  imports: [CommonModule, RouterOutlet],
  templateUrl: './admin-shell.html',
  styleUrls: ['./admin-shell.css']
})
export class AdminShellComponent implements OnInit, OnDestroy {
  username = 'Admin';
  adminRole = 'admin';
  currentRoute = 'dashboard';
  mobileMenuOpen = false;
  securityLevel = 'Standard';
  activeSessionTimeoutMinutes = 15;

  navItems = [
    { key: 'dashboard', label: 'Dashboard', description: 'Security posture and metrics', route: '/admin-shell/dashboard' },
    { key: 'users', label: 'Users', description: 'Access and account controls', route: '/admin-shell/users' },
    { key: 'settings', label: 'Security Settings', description: 'Policy and hardening', route: '/admin-shell/settings' },
    { key: 'activity', label: 'Activity Logs', description: 'Audit and threat events', route: '/admin-shell/activity' }
  ];

  private routerSub?: Subscription;
  private inactivityTimer?: ReturnType<typeof setTimeout>;
  private readonly activityEvents = ['mousemove', 'keydown', 'click', 'scroll'];
  private readonly boundActivityHandler = this.resetInactivityTimer.bind(this);

  constructor(private router: Router) {}

  ngOnInit() {
    if (!this.hasValidAdminSession()) return;

    this.username = localStorage.getItem('username') || 'Admin';
    this.applySecurityPreferences();
    this.detectCurrentRoute();

    this.routerSub = this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe(() => this.detectCurrentRoute());

    this.registerActivityListeners();
    this.resetInactivityTimer();
  }

  ngOnDestroy() {
    if (this.routerSub) this.routerSub.unsubscribe();
    this.clearInactivityTimer();
    this.unregisterActivityListeners();
  }

  private hasValidAdminSession(): boolean {
    const token = localStorage.getItem('token');
    const role = localStorage.getItem('role');

    if (!token || role !== 'admin' || this.isTokenExpired(token)) {
      this.forceAdminLogout();
      return false;
    }

    return true;
  }

  private isTokenExpired(token: string): boolean {
    try {
      const payload = token.split('.')[1];
      if (!payload) return true;
      const parsed = JSON.parse(atob(payload));
      const exp = parsed?.exp;
      if (!exp) return true;
      return Date.now() >= exp * 1000;
    } catch {
      return true;
    }
  }

  private applySecurityPreferences() {
    const raw = localStorage.getItem('adminSecuritySettings');
    if (!raw) {
      this.activeSessionTimeoutMinutes = 15;
      this.securityLevel = 'Standard';
      return;
    }

    try {
      const settings = JSON.parse(raw);
      this.activeSessionTimeoutMinutes = Number(settings.sessionTimeoutMinutes) || 15;
      if (settings.enforceMfaForAdmin && settings.enableIpAllowlist) {
        this.securityLevel = 'Hardened';
      } else if (settings.enforceMfaForAdmin || settings.enableIpAllowlist) {
        this.securityLevel = 'Elevated';
      } else {
        this.securityLevel = 'Standard';
      }
    } catch {
      this.activeSessionTimeoutMinutes = 15;
      this.securityLevel = 'Standard';
    }
  }

  private registerActivityListeners() {
    this.activityEvents.forEach(eventName => {
      window.addEventListener(eventName, this.boundActivityHandler, { passive: true });
    });
  }

  private unregisterActivityListeners() {
    this.activityEvents.forEach(eventName => {
      window.removeEventListener(eventName, this.boundActivityHandler);
    });
  }

  private clearInactivityTimer() {
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
      this.inactivityTimer = undefined;
    }
  }

  private resetInactivityTimer() {
    this.clearInactivityTimer();
    const timeoutMs = Math.max(this.activeSessionTimeoutMinutes, 1) * 60 * 1000;
    this.inactivityTimer = setTimeout(() => {
      this.forceAdminLogout('Session timed out due to inactivity.');
    }, timeoutMs);
  }

  private forceAdminLogout(reason?: string) {
    localStorage.clear();
    if (reason) {
      localStorage.setItem('adminLogoutReason', reason);
    }
    this.router.navigate(['/admin-login']);
  }

  detectCurrentRoute() {
    const url = this.router.url;
    if (url.includes('/users')) this.currentRoute = 'users';
    else if (url.includes('/settings')) this.currentRoute = 'settings';
    else if (url.includes('/activity')) this.currentRoute = 'activity';
    else this.currentRoute = 'dashboard';
  }

  navigateTo(route: string) {
    this.currentRoute = route;
    this.mobileMenuOpen = false;
    const found = this.navItems.find(item => item.key === route);
    if (found) this.router.navigate([found.route]);
  }

  toggleMobileMenu() {
    this.mobileMenuOpen = !this.mobileMenuOpen;
  }

  logout() {
    this.forceAdminLogout();
  }
}
