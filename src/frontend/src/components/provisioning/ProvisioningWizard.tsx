/**
 * Provisioning Wizard Container
 *
 * Multi-step wizard for provisioning a single IoT device:
 * 1. Select Profile
 * 2. Device Details
 * 3. Generate Credentials
 * 4. Download Credentials
 * 5. Activation Status
 */

import { useProvisioningStore } from '../../stores/provisioningStore';
import { ProfileSelectionStep } from './steps/ProfileSelectionStep';
import { DeviceDetailsStep } from './steps/DeviceDetailsStep';
import { CredentialGenerationStep } from './steps/CredentialGenerationStep';
import { CredentialDownloadStep } from './steps/CredentialDownloadStep';
import { ActivationWaitStep } from './steps/ActivationWaitStep';

const STEPS = [
  { id: 0, title: 'Select Profile' },
  { id: 1, title: 'Device Details' },
  { id: 2, title: 'Generate Credentials' },
  { id: 3, title: 'Download Credentials' },
  { id: 4, title: 'Activation Status' },
];

export function ProvisioningWizard() {
  const { currentStep, maxStepReached, nextStep, prevStep, resetWizard } = useProvisioningStore();

  const renderStep = () => {
    switch (currentStep) {
      case 0: return <ProfileSelectionStep />;
      case 1: return <DeviceDetailsStep />;
      case 2: return <CredentialGenerationStep />;
      case 3: return <CredentialDownloadStep />;
      case 4: return <ActivationWaitStep />;
      default: return <ProfileSelectionStep />;
    }
  };

  const showPrevious = currentStep > 0 && currentStep !== 2 && currentStep !== 3;
  const showNext = currentStep < 2; // Steps 0-1 show Next, 2-4 auto-advance or have custom buttons

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Progress Indicator */}
      <div className="bg-white shadow-sm rounded-lg border p-6">
        <div className="flex items-center justify-between">
          {STEPS.map((step, index) => (
            <div key={step.id} className="flex items-center">
              {/* Step Circle */}
              <div className="flex flex-col items-center">
                <button
                  onClick={() => {
                    // Only allow clicking on completed steps
                    if (index <= maxStepReached) {
                      useProvisioningStore.getState().goToStep(index);
                    }
                  }}
                  disabled={index > maxStepReached}
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm transition-colors ${
                    index === currentStep
                      ? 'bg-blue-600 text-white'
                      : index < currentStep
                      ? 'bg-green-500 text-white cursor-pointer hover:bg-green-600'
                      : 'bg-gray-300 text-gray-600 cursor-not-allowed'
                  }`}
                >
                  {index < currentStep ? '✓' : index + 1}
                </button>
                <span className={`text-xs mt-2 text-center ${
                  index === currentStep ? 'text-blue-600 font-semibold' : 'text-gray-500'
                }`}>
                  {step.title}
                </span>
              </div>

              {/* Connecting Line */}
              {index < STEPS.length - 1 && (
                <div className={`w-16 h-0.5 mx-2 mb-6 ${
                  index < currentStep ? 'bg-green-500' : 'bg-gray-300'
                }`} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div className="bg-white shadow-lg rounded-lg border p-8">
        {renderStep()}
      </div>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between">
        <button
          onClick={resetWizard}
          className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
        >
          Cancel
        </button>

        <div className="flex gap-3">
          {showPrevious && (
            <button
              onClick={prevStep}
              className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Previous
            </button>
          )}
          {showNext && (
            <button
              onClick={nextStep}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Next
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
