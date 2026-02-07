/**
 * Device Provisioning Page
 *
 * Tab container for single-device wizard and bulk CSV provisioning.
 */
import { useState, useEffect } from 'react';
import { ProvisioningWizard } from '../components/provisioning/ProvisioningWizard';
import { BulkProvisioningUpload } from '../components/provisioning/BulkProvisioningUpload';
import { useProvisioningStore } from '../stores/provisioningStore';
import { useBulkProvisioningStore } from '../stores/bulkProvisioningStore';
import { cn } from '../utils';

type TabType = 'single' | 'bulk';

export function DeviceProvisioningPage() {
  const [activeTab, setActiveTab] = useState<TabType>('single');
  const resetWizard = useProvisioningStore((state) => state.resetWizard);
  const resetBulk = useBulkProvisioningStore((state) => state.reset);

  // Reset stores on mount to ensure clean state
  useEffect(() => {
    resetWizard();
    resetBulk();
  }, [resetWizard, resetBulk]);

  // Reset wizard when switching to single device tab
  const handleTabChange = (tab: TabType) => {
    if (tab === 'single' && activeTab !== 'single') {
      resetWizard();
    }
    setActiveTab(tab);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Device Provisioning</h1>
        <p className="mt-2 text-gray-600">
          Provision new IoT devices with secure credentials
        </p>
      </div>

      {/* Tab bar */}
      <div className="border-b border-gray-300 mb-6">
        <nav className="flex space-x-8" aria-label="Tabs">
          <button
            onClick={() => handleTabChange('single')}
            className={cn(
              'py-4 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'single'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            )}
          >
            Single Device
          </button>
          <button
            onClick={() => handleTabChange('bulk')}
            className={cn(
              'py-4 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'bulk'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            )}
          >
            Bulk Provisioning
          </button>
        </nav>
      </div>

      {/* Tab content */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {activeTab === 'single' ? (
          <ProvisioningWizard />
        ) : (
          <BulkProvisioningUpload />
        )}
      </div>
    </div>
  );
}
