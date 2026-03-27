import { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { formatPhoneNumber, formatCurrency, getInitials } from '../utils/formatters';

const WorkerModal = ({ workerId, isOpen, onClose }) => {
  const [workerData, setWorkerData] = useState(null);
  const modalRef = useRef();

  // Fetch worker details when modal opens
  useEffect(() => {
    if (!workerId || !isOpen) return;

    const fetchWorker = async () => {
      try {
        const res = await fetch(`http://localhost:3000/api/workers/${workerId}`);
        const data = await res.json();

        // Map nested structure to a flat object for easier usage
        const mappedWorker = {
          id: data.worker.id,
          name: data.worker.name,
          phone: data.worker.phone,
          upi: data.worker.upi_id || 'N/A',
          zone: data.worker.pin_codes?.join(', ') || 'N/A',
          shift: data.worker.shift,
          language: data.worker.language,
          plan: data.policy?.plan || data.worker.plan,
          premium: data.policy?.weekly_premium || 0,
          coverage: data.policy?.coverage_pct || 0,
          payoutHistory: data.payouts || [],
          activityLog: data.activities || [],
        };

        setWorkerData(mappedWorker);
      } catch (err) {
        console.error(err);
      }
    };

    fetchWorker();
  }, [workerId, isOpen]);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (modalRef.current && !modalRef.current.contains(e.target)) {
        onClose();
      }
    };
    if (isOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  if (!isOpen || !workerData) return null;

  const maskedUPI = workerData.upi
    ? workerData.upi.substring(0, 5) + '****' + workerData.upi.substring(workerData.upi.length - 4)
    : 'N/A';

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex justify-center items-start z-50 p-4 overflow-y-auto">
      <div ref={modalRef} className="bg-white dark:bg-gigkavach-navy rounded-xl max-w-3xl w-full shadow-2xl overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b dark:border-gray-700 sticky top-0 bg-white dark:bg-gigkavach-navy z-10">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">{workerData.name}</h2>
          <button onClick={onClose} className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="w-5 h-5 text-gray-900 dark:text-white" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Contact Info */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Contact Info</h3>
            <p>Phone: {formatPhoneNumber(workerData.phone)}</p>
            <p>UPI: {maskedUPI}</p>
            <p>Zone: {workerData.zone}</p>
            <p>Shift: {workerData.shift || 'N/A'}</p>
            <p>Language: {workerData.language || 'N/A'}</p>
          </section>

          {/* Policy Details */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Policy Details</h3>
            <p>Tier: {workerData.plan}</p>
            <p>Premium: {formatCurrency(workerData.premium)}</p>
            <p>Coverage Status: {workerData.coverage}%</p>
          </section>

          {/* Payout History */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Last 10 Payouts</h3>
            <ul className="space-y-1 text-sm">
              {workerData.payoutHistory?.slice(0, 10).map((p, idx) => (
                <li key={idx} className="flex justify-between">
                  <span>{new Date(p.triggered_at).toLocaleDateString()}</span>
                  <span>{formatCurrency(p.final_amount)} | Status: {p.status}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* Activity Log */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Last 20 Activities</h3>
            <ul className="space-y-1 text-sm">
              {workerData.activityLog?.slice(0, 20).map((act, idx) => (
                <li key={idx}>{act.description} ({new Date(act.date).toLocaleDateString()})</li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
};

export default WorkerModal;