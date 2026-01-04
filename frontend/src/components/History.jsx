import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye } from 'lucide-react';
import { getClaimHistory } from '../api';

const History = () => {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getClaimHistory()
      .then(res => {
        setClaims(res.data);
        setLoading(false);
      })
      .catch(err => setLoading(false));
  }, []);

  const getStatusBadge = (status) => {
    const styles = {
      APPROVED: "bg-green-100 text-green-800",
      REJECTED: "bg-red-100 text-red-800",
      PARTIAL: "bg-orange-100 text-orange-800",
      MANUAL_REVIEW: "bg-yellow-100 text-yellow-800"
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${styles[status] || "bg-gray-100"}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="max-w-5xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Claim History</h2>
      
      <div className="bg-white rounded-xl shadow overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading history...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="p-4 text-sm font-semibold text-gray-600">Claim ID</th>
                  <th className="p-4 text-sm font-semibold text-gray-600">Member</th>
                  <th className="p-4 text-sm font-semibold text-gray-600">Date</th>
                  <th className="p-4 text-sm font-semibold text-gray-600">Status</th>
                  <th className="p-4 text-sm font-semibold text-gray-600">Amount</th>
                  <th className="p-4 text-sm font-semibold text-gray-600">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {claims.map((claim) => (
                  <tr key={claim.claim_id} className="hover:bg-gray-50">
                    <td className="p-4 font-mono text-sm text-gray-500">{claim.claim_id}</td>
                    <td className="p-4 font-medium">{claim.member_name}</td>
                    <td className="p-4 text-gray-500">{new Date(claim.submission_date).toLocaleDateString()}</td>
                    <td className="p-4">{getStatusBadge(claim.decision)}</td>
                    <td className="p-4 font-medium">₹{claim.approved_amount}</td>
                    <td className="p-4">
                      <Link 
                        to={`/result/${claim.claim_id}`} 
                        className="text-purple-600 hover:text-purple-800 flex items-center"
                      >
                        <Eye size={16} className="mr-1" /> View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default History;