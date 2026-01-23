/**
 * Roles Management Page
 */

import { useEffect, useState } from 'react';
import { useRoleStore } from '../stores/roleStore';
import {
  Card,
  CardContent,
  Badge,
  Button,
  Modal,
  Input,
  Select,
  Spinner,
} from '../components/ui';
import type { Role, RoleCreateRequest, RoleUpdateRequest, Permission } from '../types';

const colorOptions = [
  { value: 'red', label: 'Red' },
  { value: 'orange', label: 'Orange' },
  { value: 'yellow', label: 'Yellow' },
  { value: 'green', label: 'Green' },
  { value: 'blue', label: 'Blue' },
  { value: 'purple', label: 'Purple' },
  { value: 'pink', label: 'Pink' },
  { value: 'gray', label: 'Gray' },
  { value: 'slate', label: 'Slate' },
];

export function RolesPage() {
  const {
    roles,
    availablePermissions,
    fetchRoles,
    fetchPermissions,
    createRole,
    updateRole,
    deleteRole,
    isLoading,
    error,
    clearError,
  } = useRoleStore();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  useEffect(() => {
    fetchRoles();
    fetchPermissions();
  }, [fetchRoles, fetchPermissions]);

  const handleDelete = async () => {
    if (selectedRole) {
      await deleteRole(selectedRole.id);
      setIsDeleteModalOpen(false);
      setSelectedRole(null);
    }
  };

  const openEdit = (role: Role) => {
    setSelectedRole(role);
    setIsEditModalOpen(true);
  };

  const openDelete = (role: Role) => {
    setSelectedRole(role);
    setIsDeleteModalOpen(true);
  };

  // Group roles by hierarchy level
  const systemRoles = roles.filter((r) => r.is_system_role);
  const customRoles = roles.filter((r) => !r.is_system_role);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Roles</h1>
          <p className="mt-1 text-gray-500">Manage user roles and permissions</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>Create Role</Button>
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

      {isLoading && roles.length === 0 ? (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : (
        <div className="space-y-8">
          {/* System Roles */}
          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">System Roles</h2>
            <p className="text-sm text-gray-500 mb-4">
              Built-in roles that cannot be deleted. Only display name and description can be
              modified.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {systemRoles.map((role) => (
                <RoleCard key={role.id} role={role} onEdit={() => openEdit(role)} />
              ))}
            </div>
          </section>

          {/* Custom Roles */}
          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Custom Roles</h2>
            {customRoles.length === 0 ? (
              <Card>
                <CardContent className="text-center py-8 text-gray-500">
                  No custom roles created yet. Click "Create Role" to add one.
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {customRoles.map((role) => (
                  <RoleCard
                    key={role.id}
                    role={role}
                    onEdit={() => openEdit(role)}
                    onDelete={() => openDelete(role)}
                  />
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      {/* Create Modal */}
      <CreateRoleModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={createRole}
        permissions={availablePermissions}
      />

      {/* Edit Modal */}
      {selectedRole && (
        <EditRoleModal
          isOpen={isEditModalOpen}
          onClose={() => {
            setIsEditModalOpen(false);
            setSelectedRole(null);
          }}
          role={selectedRole}
          onUpdate={updateRole}
          permissions={availablePermissions}
        />
      )}

      {/* Delete Confirmation Modal */}
      {selectedRole && (
        <Modal
          isOpen={isDeleteModalOpen}
          onClose={() => {
            setIsDeleteModalOpen(false);
            setSelectedRole(null);
          }}
          title="Delete Role"
        >
          <div className="space-y-4">
            <p className="text-gray-600">
              Are you sure you want to delete the role{' '}
              <strong>{selectedRole.display_name}</strong>? This action cannot be undone.
            </p>
            {selectedRole.user_count > 0 && (
              <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-700 text-sm">
                This role has {selectedRole.user_count} user(s) assigned. They must be reassigned
                before deletion.
              </div>
            )}
            <div className="flex justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => {
                  setIsDeleteModalOpen(false);
                  setSelectedRole(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleDelete}
                disabled={selectedRole.user_count > 0}
              >
                Delete Role
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

interface RoleCardProps {
  role: Role;
  onEdit: () => void;
  onDelete?: () => void;
}

function RoleCard({ role, onEdit, onDelete }: RoleCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: role.color || '#6b7280' }}
            />
            <h3 className="font-semibold text-gray-900">{role.display_name}</h3>
          </div>
          <div className="flex items-center gap-1">
            {role.is_system_role && (
              <Badge className="bg-purple-100 text-purple-700" size="sm">
                System
              </Badge>
            )}
            {!role.is_active && (
              <Badge className="bg-gray-100 text-gray-500" size="sm">
                Inactive
              </Badge>
            )}
          </div>
        </div>

        <p className="text-sm text-gray-500 mb-3 line-clamp-2">
          {role.description || 'No description'}
        </p>

        <div className="flex items-center gap-4 text-xs text-gray-400 mb-3">
          <span>Level: {role.hierarchy_level}</span>
          <span>{role.user_count} user(s)</span>
        </div>

        <div className="mb-3">
          <p className="text-xs font-medium text-gray-500 mb-1">Permissions:</p>
          <div className="flex flex-wrap gap-1">
            {role.permissions.slice(0, 4).map((perm) => (
              <Badge key={perm} variant="secondary" size="sm">
                {perm}
              </Badge>
            ))}
            {role.permissions.length > 4 && (
              <Badge variant="secondary" size="sm">
                +{role.permissions.length - 4} more
              </Badge>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <Button size="sm" variant="ghost" onClick={onEdit}>
            Edit
          </Button>
          {onDelete && (
            <Button
              size="sm"
              variant="ghost"
              className="text-red-600"
              onClick={onDelete}
              disabled={role.user_count > 0}
            >
              Delete
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

interface CreateRoleModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: RoleCreateRequest) => Promise<Role>;
  permissions: Permission[];
}

function CreateRoleModal({ isOpen, onClose, onCreate, permissions }: CreateRoleModalProps) {
  const [formData, setFormData] = useState<RoleCreateRequest>({
    name: '',
    display_name: '',
    description: '',
    hierarchy_level: 50,
    color: 'blue',
    permissions: [],
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!formData.name || !formData.display_name) {
      setError('Name and display name are required');
      return;
    }

    setIsSubmitting(true);
    try {
      await onCreate(formData);
      onClose();
      setFormData({
        name: '',
        display_name: '',
        description: '',
        hierarchy_level: 50,
        color: 'blue',
        permissions: [],
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create role');
    } finally {
      setIsSubmitting(false);
    }
  };

  const togglePermission = (key: string) => {
    setFormData((prev) => ({
      ...prev,
      permissions: prev.permissions.includes(key)
        ? prev.permissions.filter((p) => p !== key)
        : [...prev.permissions, key],
    }));
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create New Role" size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Name (identifier)"
            value={formData.name}
            onChange={(e) =>
              setFormData({
                ...formData,
                name: e.target.value.toLowerCase().replace(/\s+/g, '_'),
              })
            }
            placeholder="custom_role"
            required
          />

          <Input
            label="Display Name"
            value={formData.display_name}
            onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
            placeholder="Custom Role"
            required
          />
        </div>

        <Input
          label="Description"
          value={formData.description || ''}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          placeholder="Role description..."
        />

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Hierarchy Level (1-100, lower = more access)
            </label>
            <input
              type="number"
              min="1"
              max="100"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={formData.hierarchy_level}
              onChange={(e) =>
                setFormData({ ...formData, hierarchy_level: parseInt(e.target.value) || 50 })
              }
            />
          </div>

          <Select
            label="Color"
            options={colorOptions}
            value={formData.color || ''}
            onChange={(e) => setFormData({ ...formData, color: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Permissions</label>
          <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-lg p-3 space-y-2">
            {permissions.map((perm) => (
              <label key={perm.key} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.permissions.includes(perm.key)}
                  onChange={() => togglePermission(perm.key)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm">
                  <span className="font-medium">{perm.name}</span>
                  <span className="text-gray-500 ml-2">({perm.key})</span>
                </span>
              </label>
            ))}
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Create Role
          </Button>
        </div>
      </form>
    </Modal>
  );
}

interface EditRoleModalProps {
  isOpen: boolean;
  onClose: () => void;
  role: Role;
  onUpdate: (id: string, data: RoleUpdateRequest) => Promise<Role>;
  permissions: Permission[];
}

function EditRoleModal({ isOpen, onClose, role, onUpdate, permissions }: EditRoleModalProps) {
  const [formData, setFormData] = useState<RoleUpdateRequest>({
    display_name: role.display_name,
    description: role.description || '',
    hierarchy_level: role.hierarchy_level,
    color: role.color || '',
    permissions: role.permissions,
    is_active: role.is_active,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setFormData({
      display_name: role.display_name,
      description: role.description || '',
      hierarchy_level: role.hierarchy_level,
      color: role.color || '',
      permissions: role.permissions,
      is_active: role.is_active,
    });
  }, [role]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    setIsSubmitting(true);
    try {
      // For system roles, only send allowed fields
      const updateData = role.is_system_role
        ? {
            display_name: formData.display_name,
            description: formData.description,
            color: formData.color,
          }
        : formData;

      await onUpdate(role.id, updateData);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update role');
    } finally {
      setIsSubmitting(false);
    }
  };

  const togglePermission = (key: string) => {
    setFormData((prev) => ({
      ...prev,
      permissions: prev.permissions?.includes(key)
        ? prev.permissions.filter((p) => p !== key)
        : [...(prev.permissions || []), key],
    }));
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Edit Role: ${role.display_name}`} size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {role.is_system_role && (
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-700 text-sm">
            This is a system role. Only display name, description, and color can be modified.
          </div>
        )}

        <Input
          label="Display Name"
          value={formData.display_name || ''}
          onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
          required
        />

        <Input
          label="Description"
          value={formData.description || ''}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
        />

        <div className="grid grid-cols-2 gap-4">
          {!role.is_system_role && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Hierarchy Level
              </label>
              <input
                type="number"
                min="1"
                max="100"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={formData.hierarchy_level || 50}
                onChange={(e) =>
                  setFormData({ ...formData, hierarchy_level: parseInt(e.target.value) || 50 })
                }
              />
            </div>
          )}

          <Select
            label="Color"
            options={colorOptions}
            value={formData.color || ''}
            onChange={(e) => setFormData({ ...formData, color: e.target.value })}
          />
        </div>

        {!role.is_system_role && (
          <>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
                Role is active
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Permissions</label>
              <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-lg p-3 space-y-2">
                {permissions.map((perm) => (
                  <label key={perm.key} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.permissions?.includes(perm.key) || false}
                      onChange={() => togglePermission(perm.key)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm">
                      <span className="font-medium">{perm.name}</span>
                      <span className="text-gray-500 ml-2">({perm.key})</span>
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </>
        )}

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
