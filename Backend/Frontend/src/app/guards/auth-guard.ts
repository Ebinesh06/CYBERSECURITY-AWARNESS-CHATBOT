import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

export const authGuard: CanActivateFn = (route, state) => {
  const router = inject(Router);
  const platformId = inject(PLATFORM_ID);

  // Check if running in browser (not SSR)
  if (!isPlatformBrowser(platformId)) {
    return true; // Allow SSR to proceed
  }

  const requiredRole = route.data?.['role'];

  // Check if user has a token (is logged in)
  const token = localStorage.getItem('token');
  if (!token) {
    // Redirect admins to admin-login, others to user-login
    if (requiredRole === 'admin') {
      router.navigate(['/admin-login']);
    } else {
      router.navigate(['/user-login']);
    }
    return false;
  }

  // Check if route requires a specific role
  if (requiredRole) {
    const userRole = localStorage.getItem('role');
    if (userRole !== requiredRole) {
      // Redirect based on role mismatch
      if (requiredRole === 'admin') {
        router.navigate(['/admin-login']);
      } else {
        router.navigate(['/chat']);
      }
      return false;
    }
  }

  // User is authenticated and authorized
  return true;
};
