import { Routes } from '@angular/router';
import { UserLoginComponent } from './user-login/user-login';
import { AdminLoginComponent } from './admin-login/admin-login';
import { ChatComponent } from './chat/chat';
import { AdminDashboardComponent } from './admin-dashboard/admin-dashboard';
import { AdminShellComponent } from './admin-shell/admin-shell';
import { AdminUsersComponent } from './admin-users/admin-users';
import { AdminSettingsComponent } from './admin-settings/admin-settings';
import { AdminActivityComponent } from './admin-activity/admin-activity';
import { authGuard } from './guards/auth-guard';

export const routes: Routes = [
  // Default route redirects to user login
  { path: '', redirectTo: 'user-login', pathMatch: 'full' },
  
  // Login routes (no auth required)
  { 
    path: 'user-login', 
    component: UserLoginComponent 
  },
  { 
    path: 'admin-login', 
    component: AdminLoginComponent 
  },
  
  // Chat route (auth required, user role)
  { 
    path: 'chat', 
    component: ChatComponent,
    canActivate: [authGuard]
  },
  
  // Admin routes (auth required, admin role) - AdminShell as parent
  { 
    path: 'admin-shell',
    component: AdminShellComponent,
    canActivate: [authGuard],
    data: { role: 'admin' },
    children: [
      { 
        path: '', 
        redirectTo: 'dashboard', 
        pathMatch: 'full'
      },
      {
        path: 'dashboard',
        component: AdminDashboardComponent
      },
      {
        path: 'users',
        component: AdminUsersComponent
      },
      {
        path: 'settings',
        component: AdminSettingsComponent
      },
      {
        path: 'activity',
        component: AdminActivityComponent
      }
    ]
  },
  
  // Fallback - unknown routes go to user login
  { path: '**', redirectTo: 'user-login' }
];
