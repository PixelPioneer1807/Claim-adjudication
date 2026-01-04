import React, { useEffect, useState } from 'react';
import { useParams, useLocation, Link } from 'react-router-dom';
import { CheckCircle, XCircle, AlertTriangle, ArrowLeft } from 'lucide-react';
import { getClaimDetails } from '../api';

const ClaimResult = () => {
  const { claimId } = useParams();
  const location = useLocation();
  // Use state passed from navigation OR fetch fresh
  const [claim, setClaim] = useState(location.state?.result || null);
  const [loading, setLoading] = useState(!claim);

  useEffect(() => {
    if (!claim) {
      getClaimDetails(claimId)
        .then(res => {
          setClaim(res.data);
          setLoading(false);
        })
        .catch(err => setLoading(false));
    }
  }, [claimId, claim]);

  if (loading) return <div className="p-10 text-center">Loading result...</div>;
  if (!claim) return <div className="p-10 text-center text-red-500">Claim not found</div>;

  const StatusIcon = {
    APPROVED: <CheckCircle className="w-16 h-16 text-green-500" />,
    REJECTED: <XCircle className="w-16 h-16 text-red-500" />,
    PARTIAL: <AlertTriangle className="w-16 h-16 text-orange-500" />,
    MANUAL_REVIEW: <AlertTriangle className="w-16 h-16 text-yellow-500" />
  }[claim.decision];

  const statusColor = {
    APPROVED: "bg-green-50 border-green-200 text-green-800",
    REJECTED: "bg-red-50 border-red-200 text-red-800",
    PARTIAL: "bg-orange-50 border-orange-200 text-orange-800",
    MANUAL_REVIEW: "bg-yellow-50 border-yellow-200 text-yellow-800"
  }[claim.decision];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Link to="/" className="inline-flex items-center text-gray-500 hover:text-purple-600">
        <ArrowLeft size={18} className="mr-2" /> Back to Home
      </Link>

      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        {/* Header Banner */}
        <div className={`p-8 text-center border-b ${statusColor} bg-opacity-50`}>
          <div className="flex justify-center mb-4">{StatusIcon}</div>
          <h1 className="text-3xl font-bold mb-2">{claim.decision}</h1>
          <p className="opacity-80">Claim ID: {claim.claim_id}</p>
        </div>

        <div className="p-8 space-y-8">
          {/* Financials */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-6 text-center">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500 mb-1">Approved Amount</p>
              <p className="text-2xl font-bold text-green-600">₹{claim.approved_amount}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500 mb-1">Confidence Score</p>
              <p className="text-2xl font-bold text-purple-600">{(claim.confidence_score * 100).toFixed(0)}%</p>
            </div>
            {claim.total_amount && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500 mb-1">Claimed Amount</p>
                <p className="text-2xl font-bold text-gray-700">₹{claim.total_amount}</p>
              </div>
            )}
          </div>

          {/* Reasoning Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-800 border-b pb-2">Adjudication Details</h3>
            
            {claim.rejection_reasons && claim.rejection_reasons.length > 0 && (
              <div className="bg-red-50 p-4 rounded-md">
                <span className="font-semibold text-red-700">Rejection Reasons:</span>
                <ul className="list-disc list-inside mt-2 text-red-600">
                  {claim.rejection_reasons.map(r => <li key={r}>{r}</li>)}
                </ul>
              </div>
            )}

            {Object.keys(claim.deductions || {}).length > 0 && (
              <div className="bg-blue-50 p-4 rounded-md">
                <span className="font-semibold text-blue-700">Deductions Applied:</span>
                <ul className="list-disc list-inside mt-2 text-blue-600">
                  {Object.entries(claim.deductions).map(([key, val]) => (
                    <li key={key} className="capitalize">{key.replace('_', ' ')}: -₹{val}</li>
                  ))}
                </ul>
              </div>
            )}
            
            <div>
              <p className="font-semibold text-gray-700">AI Reasoning & Notes:</p>
              <p className="text-gray-600 mt-1">{claim.notes}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClaimResult;