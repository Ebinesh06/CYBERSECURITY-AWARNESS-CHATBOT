import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="management-container">
      <h1>👥 User Management</h1>
      <p>Manage user accounts, roles, and permissions.</p>
      
      <div class="management-section">
        <h2>Users List</h2>
        <div class="users-table">
          <div class="table-header">
            <div class="col">Username</div>
            <div class="col">Role</div>
            <div class="col">Actions</div>
          </div>
          <div class="table-row">
            <div class="col">admin</div>
            <div class="col"><span class="badge admin-badge">Admin</span></div>
            <div class="col"><button>Edit</button> <button>Delete</button></div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .management-container {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }

    h1 {
      margin: 0 0 16px;
      font-size: 2rem;
      color: #0f172a;
      font-weight: 700;
    }

    p {
      color: #475569;
      margin: 0 0 32px;
    }

    h2 {
      font-size: 1.3rem;
      color: #1e293b;
      margin: 0 0 16px;
    }

    .management-section {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 24px;
    }

    .users-table {
      display: flex;
      flex-direction: column;
      gap: 0;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
    }

    .table-header {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 16px;
      background: #f1f5f9;
      padding: 12px 16px;
      font-weight: 600;
      color: #475569;
      border-bottom: 1px solid #e2e8f0;
    }

    .table-row {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 16px;
      padding: 12px 16px;
      align-items: center;
      border-bottom: 1px solid #e2e8f0;
    }

    .table-row:last-child {
      border-bottom: none;
    }

    .col {
      color: #1e293b;
    }

    .badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 600;
    }

    .admin-badge {
      background: #dbeafe;
      color: #0369a1;
    }

    button {
      padding: 6px 12px;
      margin-right: 8px;
      background: #2563eb;
      color: #ffffff;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.85rem;
      font-weight: 500;
    }

    button:hover {
      background: #1d4ed8;
    }
  `]
})
export class UserManagementComponent implements OnInit {
  constructor(private router: Router) {}

  ngOnInit() {
    // Verify user is admin
    const role = localStorage.getItem('role');
    if (role !== 'admin') {
      this.router.navigate(['/chat']);
    }
  }
}
