import {
  ChartColumn,
  FileSpreadsheet,
  FileText,
  LayoutDashboard,
  Settings,
  Users,
  type LucideIcon,
} from 'lucide-react'
import type { Role } from '../lib/types'

/**
 * The list of modules shown in the navigation menu and on the dashboard.
 * To add a new module later: add an entry here and a matching route in App.tsx.
 */
export interface AppModule {
  path: string
  label: string
  description: string
  icon: LucideIcon
  /** Which roles may open this module. */
  roles: Role[]
  /** Show on the dashboard as a quick-access card. */
  onDashboard: boolean
}

export const MODULES: AppModule[] = [
  {
    path: '/',
    label: 'Dashboard',
    description: 'Overview of your office workspace',
    icon: LayoutDashboard,
    roles: ['admin', 'staff'],
    onDashboard: false,
  },
  {
    path: '/excel',
    label: 'Excel Tools',
    description: 'Create, read and convert Excel spreadsheets',
    icon: FileSpreadsheet,
    roles: ['admin', 'staff'],
    onDashboard: true,
  },
  {
    path: '/pdf',
    label: 'PDF Tools',
    description: 'Merge, split and generate PDF documents',
    icon: FileText,
    roles: ['admin', 'staff'],
    onDashboard: true,
  },
  {
    path: '/reports',
    label: 'Activity & Reports',
    description: 'See recent activity and history',
    icon: ChartColumn,
    roles: ['admin', 'staff'],
    onDashboard: true,
  },
  {
    path: '/users',
    label: 'User Management',
    description: 'Manage staff accounts and roles',
    icon: Users,
    roles: ['admin'],
    onDashboard: true,
  },
  {
    path: '/settings',
    label: 'Settings',
    description: 'Your profile, app install and sign out',
    icon: Settings,
    roles: ['admin', 'staff'],
    onDashboard: true,
  },
]

export function modulesForRole(role: Role | undefined): AppModule[] {
  if (!role) return []
  return MODULES.filter((m) => m.roles.includes(role))
}
