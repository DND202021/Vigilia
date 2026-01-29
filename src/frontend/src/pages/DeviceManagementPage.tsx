/**
 * Device Management Page - CRUD for IoT devices
 */

import { useEffect, useState } from 'react';
import { useDeviceStore } from '../stores/deviceStore';
import { buildingsApi } from '../services/api';
import type { IoTDevice, IoTDeviceCreateRequest, Building, FloorPlan, DeviceType, DeviceStatus } from '../types';

const DEVICE_TYPES: { value: DeviceType; label: string }[] = [
  { value: 'microphone', label: 'Microphone' },
  { value: 'camera', label: 'Camera' },
  { value: 'sensor', label: 'Sensor' },
  { value: 'gateway', label: 'Gateway' },
  { value: 'other', label: 'Other' },
];

const DEVICE_STATUSES: { value: DeviceStatus; label: string; color: string }[] = [
  { value: 'online', label: 'Online', color: 'bg-green-100 text-green-800' },
  { value: 'offline', label: 'Offline', color: 'bg-gray-100 text-gray-800' },
  { value: 'alert', label: 'Alert', color: 'bg-red-100 text-red-800' },
  { value: 'maintenance', label: 'Maintenance', color: 'bg-yellow-100 text-yellow-800' },
  { value: 'error', label: 'Error', color: 'bg-orange-100 text-orange-800' },
];

function getStatusBadge(status: DeviceStatus) {
  const s = DEVICE_STATUSES.find((ds) => ds.value === status);
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${s?.color || 'bg-gray-100 text-gray-800'}`}>
      <span className={`w-2 h-2 rounded-full mr-1.5 ${
        status === 'online' ? 'bg-green-500' :
        status === 'alert' ? 'bg-red-500 animate-pulse' :
        status === 'offline' ? 'bg-gray-400' :
        status === 'maintenance' ? 'bg-yellow-500' : 'bg-orange-500'
      }`} />
      {s?.label || status}
    </span>
  );
}

function getDeviceTypeIcon(type: DeviceType) {
  switch (type) {
    case 'microphone': return '🎙️';
    case 'camera': return '📷';
    case 'sensor': return '📡';
    case 'gateway': return '🔌';
    default: return '📱';
  }
}

export function DeviceManagementPage() {
  const {
    devices, totalDevices, isLoading, error,
    fetchDevices, createDevice, updateDevice, deleteDevice, clearError,
  } = useDeviceStore();

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingDevice, setEditingDevice] = useState<IoTDevice | null>(null);
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [floorPlans, setFloorPlans] = useState<FloorPlan[]>([]);
  const [filterBuilding, setFilterBuilding] = useState<string>('');
  const [filterType, setFilterType] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');

  useEffect(() => {
    fetchDevices({
      building_id: filterBuilding || undefined,
      device_type: filterType || undefined,
      status: filterStatus || undefined,
    });
  }, [fetchDevices, filterBuilding, filterType, filterStatus]);

  useEffect(() => {
    buildingsApi.list({ page_size: 100 }).then((res) => setBuildings(res.items));
  }, []);

  const loadFloorPlans = async (buildingId: string) => {
    if (!buildingId) { setFloorPlans([]); return; }
    const plans = await buildingsApi.getFloorPlans(buildingId);
    setFloorPlans(plans);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">IoT Devices</h1>
          <p className="text-sm text-gray-500 mt-1">{totalDevices} devices registered</p>
        </div>
        <button
          onClick={() => setShowCreateDialog(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          + Add Device
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex justify-between items-center">
          <span className="text-red-800">{error}</span>
          <button onClick={clearError} className="text-red-600 hover:text-red-800">Dismiss</button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-4 bg-white p-4 rounded-lg shadow-sm border">
        <select
          value={filterBuilding}
          onChange={(e) => setFilterBuilding(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Buildings</option>
          {buildings.map((b) => (
            <option key={b.id} value={b.id}>{b.name}</option>
          ))}
        </select>

        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Types</option>
          {DEVICE_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Statuses</option>
          {DEVICE_STATUSES.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
      </div>

      {/* Device Table */}
      <div className="bg-white shadow-sm rounded-lg border overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Device</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Seen</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-gray-500">Loading devices...</td>
              </tr>
            ) : devices.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-gray-500">No devices found</td>
              </tr>
            ) : (
              devices.map((device) => (
                <tr key={device.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      <span className="text-xl mr-3">{getDeviceTypeIcon(device.device_type)}</span>
                      <div>
                        <div className="font-medium text-gray-900">{device.name}</div>
                        {(device.serial_number || device.ip_address) && (
                          <div className="text-sm text-gray-500">{device.serial_number || device.ip_address}</div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700 capitalize">{device.device_type}</td>
                  <td className="px-6 py-4">{getStatusBadge(device.status)}</td>
                  <td className="px-6 py-4 text-sm text-gray-700">{device.location_name || '—'}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {device.last_seen ? new Date(device.last_seen).toLocaleString() : 'Never'}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <button
                      onClick={() => { setEditingDevice(device); loadFloorPlans(device.building_id || ''); }}
                      className="text-blue-600 hover:text-blue-800 mr-3"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => { if (confirm('Delete this device?')) deleteDevice(device.id); }}
                      className="text-red-600 hover:text-red-800"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create/Edit Dialog */}
      {(showCreateDialog || editingDevice) && (
        <DeviceDialog
          device={editingDevice}
          buildings={buildings}
          floorPlans={floorPlans}
          onLoadFloorPlans={loadFloorPlans}
          onSave={async (data) => {
            if (editingDevice) {
              await updateDevice(editingDevice.id, data);
            } else {
              await createDevice(data as unknown as IoTDeviceCreateRequest);
            }
            setShowCreateDialog(false);
            setEditingDevice(null);
          }}
          onClose={() => { setShowCreateDialog(false); setEditingDevice(null); }}
        />
      )}
    </div>
  );
}

function DeviceDialog({
  device,
  buildings,
  floorPlans,
  onLoadFloorPlans,
  onSave,
  onClose,
}: {
  device: IoTDevice | null;
  buildings: Building[];
  floorPlans: FloorPlan[];
  onLoadFloorPlans: (buildingId: string) => void;
  onSave: (data: Record<string, unknown>) => Promise<void>;
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    name: device?.name || '',
    device_type: device?.device_type || 'microphone',
    serial_number: device?.serial_number || '',
    ip_address: device?.ip_address || '',
    model: device?.model || '',
    firmware_version: device?.firmware_version || '',
    manufacturer: device?.manufacturer || 'Axis',
    building_id: device?.building_id || '',
    floor_plan_id: device?.floor_plan_id || '',
    location_name: device?.location_name || '',
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const data: Record<string, unknown> = { ...form };
      // Remove empty strings
      Object.keys(data).forEach((key) => {
        if (data[key] === '') data[key] = undefined;
      });
      await onSave(data);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
        <h2 className="text-xl font-bold mb-4">{device ? 'Edit Device' : 'Add New Device'}</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Name *</label>
            <input
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="mt-1 w-full border rounded-lg px-3 py-2"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Type *</label>
              <select
                value={form.device_type}
                onChange={(e) => setForm({ ...form, device_type: e.target.value as DeviceType })}
                className="mt-1 w-full border rounded-lg px-3 py-2"
              >
                {DEVICE_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Manufacturer</label>
              <input
                type="text"
                value={form.manufacturer}
                onChange={(e) => setForm({ ...form, manufacturer: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Serial Number</label>
              <input
                type="text"
                value={form.serial_number}
                onChange={(e) => setForm({ ...form, serial_number: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">IP Address</label>
              <input
                type="text"
                value={form.ip_address}
                onChange={(e) => setForm({ ...form, ip_address: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Model</label>
              <input
                type="text"
                value={form.model}
                onChange={(e) => setForm({ ...form, model: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Firmware Version</label>
              <input
                type="text"
                value={form.firmware_version}
                onChange={(e) => setForm({ ...form, firmware_version: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Building *</label>
            <select
              required
              value={form.building_id}
              onChange={(e) => {
                setForm({ ...form, building_id: e.target.value, floor_plan_id: '' });
                onLoadFloorPlans(e.target.value);
              }}
              className="mt-1 w-full border rounded-lg px-3 py-2"
            >
              <option value="">Select building...</option>
              {buildings.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Floor Plan</label>
            <select
              value={form.floor_plan_id}
              onChange={(e) => setForm({ ...form, floor_plan_id: e.target.value })}
              className="mt-1 w-full border rounded-lg px-3 py-2"
            >
              <option value="">Select floor...</option>
              {floorPlans.map((fp) => (
                <option key={fp.id} value={fp.id}>
                  Floor {fp.floor_number}{fp.floor_name ? ` - ${fp.floor_name}` : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Location Name</label>
            <input
              type="text"
              placeholder="e.g., Room 428, Hallway B"
              value={form.location_name}
              onChange={(e) => setForm({ ...form, location_name: e.target.value })}
              className="mt-1 w-full border rounded-lg px-3 py-2"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : device ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
