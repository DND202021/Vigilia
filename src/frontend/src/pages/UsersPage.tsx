/**
 * Users Management Page
 */

import { useEffect, useState } from 'react';
import { useUserStore } from '../stores/userStore';
import { useRoleStore } from '../stores/roleStore';
import {
  Card,
  CardContent,
  Badge,
  Button,
  Select,
  Modal,
  Input,
  Spinner,
} from '../components/ui';
import { formatRelativeTime, cn } from '../utils';
import type { UserFull, UserCreateRequest, UserUpdateRequest, Role } from '../types';

const statusFilterOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
];

export function UsersPage() {
  const {
    users,
    stats,
    fetchUsers,
    fetchStats,
    createUser,
    updateUser,
    deactivateUser,
    activateUser,
    verifyUser,
    deleteUser,
    isLoading,
    error,
    clearError,
    total,
    page,
    pageSize,
    setPage,
  } = useUserStore();

  const { roles, fetchRoles } = useRoleStore();

  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserFull | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  // Fetch data on mount and filter change
  useEffect(() => {
    fetchRoles();
    fetchStats();
  }, [fetchRoles, fetchStats]);

  useEffect(() => {
    const params: Record<string, unknown> = { page, page_size: pageSize };
    if (roleFilter) params.role_id = roleFilter;
    if (statusFilter === 'active') params.is_active = true;
    if (statusFilter === 'inactive') params.is_active = false;
    if (searchQuery) params.search = searchQuery;
    fetchUsers(params);
  }, [fetchUsers, roleFilter, statusFilter, searchQuery, page, pageSize]);

  const roleFilterOptions = [
    { value: '', label: 'All Roles' },
    ...roles.map((r) => ({ value: r.id, label: r.display_name })),
  ];

  const handleStatusToggle = async (user: UserFull) => {
    if (user.is_active) {
      await deactivateUser(user.id);
    } else {
      await activateUser(user.id);
    }
  };

  const handleVerify = async (user: UserFull) => {
    await verifyUser(user.id);
  };

  const handleDelete = async () => {
    if (selectedUser) {
      await deleteUser(selectedUser.id);
      setIsDeleteModalOpen(false);
      setSelectedUser(null);
    }
  };

  const openEdit = (user: UserFull) => {
    setSelectedUser(user);
    setIsEditModalOpen(true);
  };

  const openDelete = (user: UserFull) => {
    setSelectedUser(user);
    setIsDeleteModalOpen(true);
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Users</h1>
          <p className="mt-1 text-gray-500">Manage user accounts and permissions</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>Add User</Button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard label="Total Users" count={stats.total} color="blue" />
          <StatCard label="Active" count={stats.active} color="green" />
          <StatCard label="Inactive" count={stats.inactive} color="gray" />
          <StatCard label="Verified" count={stats.verified} color="purple" />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="w-48">
          <Select
            options={roleFilterOptions}
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="w-48">
          <Select
            options={statusFilterOptions}
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="flex-1 min-w-[200px]">
          <Input
            placeholder="Search by email, name, or badge..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between">
          <span className="text-red-700">{error}</span>
          <button onClick={clearError} className="text-red-500 hover:text-red-700">
            Dismiss
          </button>
        </div>
      )}

      {/* Users Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading && users.length === 0 ? (
            <div className="flex justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-12 text-gray-500">No users found</div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        User
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Role
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Agency
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Created
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {users.map((user) => (
                      <UserRow
                        key={user.id}
                        user={user}
                        onEdit={() => openEdit(user)}
                        onDelete={() => openDelete(user)}
                        onStatusToggle={() => handleStatusToggle(user)}
                        onVerify={() => handleVerify(user)}
                      />
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200">
                  <div className="text-sm text-gray-500">
                    Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of{' '}
                    {total} users
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={page <= 1}
                      onClick={() => setPage(page - 1)}
                    >
                      Previous
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={page >= totalPages}
                      onClick={() => setPage(page + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Create Modal */}
      <CreateUserModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={createUser}
        roles={roles}
      />

      {/* Edit Modal */}
      {selectedUser && (
        <EditUserModal
          isOpen={isEditModalOpen}
          onClose={() => {
            setIsEditModalOpen(false);
            setSelectedUser(null);
          }}
          user={selectedUser}
          onUpdate={updateUser}
          roles={roles}
        />
      )}

      {/* Delete Confirmation Modal */}
      {selectedUser && (
        <Modal
          isOpen={isDeleteModalOpen}
          onClose={() => {
            setIsDeleteModalOpen(false);
            setSelectedUser(null);
          }}
          title="Delete User"
        >
          <div className="space-y-4">
            <p className="text-gray-600">
              Are you sure you want to delete <strong>{selectedUser.full_name}</strong>? This action
              cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => {
                  setIsDeleteModalOpen(false);
                  setSelectedUser(null);
                }}
              >
                Cancel
              </Button>
              <Button variant="danger" onClick={handleDelete}>
                Delete User
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

interface StatCardProps {
  label: string;
  count: number;
  color: 'green' | 'blue' | 'purple' | 'gray';
}

function StatCard({ label, count, color }: StatCardProps) {
  const colorStyles = {
    green: 'bg-green-50 text-green-700 border-green-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
    gray: 'bg-gray-50 text-gray-700 border-gray-200',
  };

  return (
    <div className={cn('p-4 rounded-lg border', colorStyles[color])}>
      <p className="text-2xl font-bold">{count}</p>
      <p className="text-sm">{label}</p>
    </div>
  );
}

interface UserRowProps {
  user: UserFull;
  onEdit: () => void;
  onDelete: () => void;
  onStatusToggle: () => void;
  onVerify: () => void;
}

function UserRow({ user, onEdit, onDelete, onStatusToggle, onVerify }: UserRowProps) {
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold',
              user.is_active ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'
            )}
          >
            {user.full_name
              .split(' ')
              .map((n) => n[0])
              .join('')
              .toUpperCase()
              .slice(0, 2)}
          </div>
          <div>
            <div className="font-medium text-gray-900">{user.full_name}</div>
            <div className="text-sm text-gray-500">{user.email}</div>
            {user.badge_number && (
              <div className="text-xs text-gray-400">Badge: {user.badge_number}</div>
            )}
          </div>
        </div>
      </td>
      <td className="px-6 py-4">
        <Badge className="bg-gray-100 text-gray-700">
          {user.role_display_name}
        </Badge>
      </td>
      <td className="px-6 py-4 text-sm text-gray-500">{user.agency?.name || '-'}</td>
      <td className="px-6 py-4">
        <div className="flex flex-col gap-1">
          <Badge className={user.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}>
            {user.is_active ? 'Active' : 'Inactive'}
          </Badge>
          {user.is_verified ? (
            <Badge className="bg-blue-100 text-blue-700" size="sm">
              Verified
            </Badge>
          ) : (
            <Badge className="bg-yellow-100 text-yellow-700" size="sm">
              Unverified
            </Badge>
          )}
        </div>
      </td>
      <td className="px-6 py-4 text-sm text-gray-500">{formatRelativeTime(user.created_at)}</td>
      <td className="px-6 py-4 text-right">
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="ghost" onClick={onEdit}>
            Edit
          </Button>
          {!user.is_verified && (
            <Button size="sm" variant="outline" onClick={onVerify}>
              Verify
            </Button>
          )}
          <Button
            size="sm"
            variant={user.is_active ? 'outline' : 'secondary'}
            onClick={onStatusToggle}
          >
            {user.is_active ? 'Deactivate' : 'Activate'}
          </Button>
          <Button size="sm" variant="ghost" className="text-red-600" onClick={onDelete}>
            Delete
          </Button>
        </div>
      </td>
    </tr>
  );
}

interface CreateUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: UserCreateRequest) => Promise<UserFull>;
  roles: Role[];
}

function CreateUserModal({ isOpen, onClose, onCreate, roles }: CreateUserModalProps) {
  const [formData, setFormData] = useState<UserCreateRequest>({
    email: '',
    password: '',
    full_name: '',
    role_id: '',
    badge_number: '',
    phone: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!formData.email || !formData.password || !formData.full_name) {
      setError('Email, password, and full name are required');
      return;
    }

    if (formData.password.length < 12) {
      setError('Password must be at least 12 characters');
      return;
    }

    setIsSubmitting(true);
    try {
      await onCreate({
        ...formData,
        role_id: formData.role_id || undefined,
        badge_number: formData.badge_number || undefined,
        phone: formData.phone || undefined,
      });
      onClose();
      setFormData({
        email: '',
        password: '',
        full_name: '',
        role_id: '',
        badge_number: '',
        phone: '',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
    } finally {
      setIsSubmitting(false);
    }
  };

  const roleOptions = [
    { value: '', label: 'Select Role' },
    ...roles.map((r) => ({ value: r.id, label: r.display_name })),
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add New User">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <Input
          label="Full Name"
          value={formData.full_name}
          onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
          placeholder="John Doe"
          required
        />

        <Input
          label="Email"
          type="email"
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          placeholder="john@example.com"
          required
        />

        <Input
          label="Password"
          type="password"
          value={formData.password}
          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          placeholder="Minimum 12 characters"
          required
        />

        <Select
          label="Role"
          options={roleOptions}
          value={formData.role_id || ''}
          onChange={(e) => setFormData({ ...formData, role_id: e.target.value })}
        />

        <Input
          label="Badge Number"
          value={formData.badge_number || ''}
          onChange={(e) => setFormData({ ...formData, badge_number: e.target.value })}
          placeholder="Optional"
        />

        <Input
          label="Phone"
          type="tel"
          value={formData.phone || ''}
          onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
          placeholder="Optional"
        />

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Add User
          </Button>
        </div>
      </form>
    </Modal>
  );
}

interface EditUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: UserFull;
  onUpdate: (id: string, data: UserUpdateRequest) => Promise<UserFull>;
  roles: Role[];
}

function EditUserModal({ isOpen, onClose, user, onUpdate, roles }: EditUserModalProps) {
  const [formData, setFormData] = useState<UserUpdateRequest>({
    full_name: user.full_name,
    email: user.email,
    role_id: user.role?.id,
    badge_number: user.badge_number || '',
    phone: user.phone || '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setFormData({
      full_name: user.full_name,
      email: user.email,
      role_id: user.role?.id,
      badge_number: user.badge_number || '',
      phone: user.phone || '',
    });
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    setIsSubmitting(true);
    try {
      await onUpdate(user.id, {
        ...formData,
        badge_number: formData.badge_number || undefined,
        phone: formData.phone || undefined,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user');
    } finally {
      setIsSubmitting(false);
    }
  };

  const roleOptions = [
    { value: '', label: 'Select Role' },
    ...roles.map((r) => ({ value: r.id, label: r.display_name })),
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit User">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <Input
          label="Full Name"
          value={formData.full_name || ''}
          onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
          required
        />

        <Input
          label="Email"
          type="email"
          value={formData.email || ''}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          required
        />

        <Select
          label="Role"
          options={roleOptions}
          value={formData.role_id || ''}
          onChange={(e) => setFormData({ ...formData, role_id: e.target.value })}
        />

        <Input
          label="Badge Number"
          value={formData.badge_number || ''}
          onChange={(e) => setFormData({ ...formData, badge_number: e.target.value })}
        />

        <Input
          label="Phone"
          type="tel"
          value={formData.phone || ''}
          onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
        />

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Save Changes
          </Button>
        </div>
      </form>
    </Modal>
  );
}
