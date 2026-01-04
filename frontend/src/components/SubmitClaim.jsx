import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileText, X, Loader2 } from 'lucide-react';
import { submitClaim } from '../api';

const SubmitClaim = () => {
  const navigate = useNavigate();
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState({
    member_id: '',
    member_name: '',
    treatment_date: new Date().toISOString().split('T')[0],
    member_join_date: ''
  });

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setIsDragging(true);
    else setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleFiles = (newFiles) => {
    const validFiles = Array.from(newFiles).filter(file => 
      ['image/jpeg', 'image/png', 'application/pdf'].includes(file.type)
    );
    setFiles(prev => [...prev, ...validFiles]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (files.length === 0) {
      setError("Please upload at least one document (Bill or Prescription)");
      return;
    }

    setIsLoading(true);
    setError('');
    
    const data = new FormData();
    Object.keys(formData).forEach(key => data.append(key, formData[key]));
    files.forEach(file => data.append('documents', file));

    try {
      const response = await submitClaim(data);
      // Redirect to result page with the claim ID
      navigate(`/result/${response.data.claim_id}`, { state: { result: response.data } });
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to submit claim. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-md overflow-hidden p-8">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Submit New OPD Claim</h2>
      
      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-md border border-red-200">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Member ID</label>
            <input
              type="text"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:outline-none"
              placeholder="e.g. EMP001"
              value={formData.member_id}
              onChange={e => setFormData({...formData, member_id: e.target.value})}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Member Name</label>
            <input
              type="text"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:outline-none"
              placeholder="e.g. Rajesh Kumar"
              value={formData.member_name}
              onChange={e => setFormData({...formData, member_name: e.target.value})}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Treatment Date</label>
            <input
              type="date"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:outline-none"
              value={formData.treatment_date}
              onChange={e => setFormData({...formData, treatment_date: e.target.value})}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Join Date (Optional)</label>
            <input
              type="date"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:outline-none"
              value={formData.member_join_date}
              onChange={e => setFormData({...formData, member_join_date: e.target.value})}
            />
          </div>
        </div>

        {/* Drag and Drop Area */}
        <div 
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
            isDragging ? 'border-purple-500 bg-purple-50' : 'border-gray-300 hover:border-purple-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <UploadCloud className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-2">Drag and drop your medical bills & prescriptions here</p>
          <p className="text-sm text-gray-400 mb-4">Supported: JPG, PNG, PDF</p>
          <input
            type="file"
            multiple
            className="hidden"
            id="file-upload"
            onChange={(e) => handleFiles(e.target.files)}
          />
          <label 
            htmlFor="file-upload"
            className="px-4 py-2 bg-purple-100 text-purple-700 rounded-md cursor-pointer hover:bg-purple-200 font-medium"
          >
            Browse Files
          </label>
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="space-y-2">
            {files.map((file, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <FileText className="w-5 h-5 text-purple-600" />
                  <span className="text-sm text-gray-700">{file.name}</span>
                </div>
                <button 
                  type="button"
                  onClick={() => setFiles(files.filter((_, i) => i !== index))}
                  className="text-gray-400 hover:text-red-500"
                >
                  <X size={18} />
                </button>
              </div>
            ))}
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-purple-700 text-white py-3 rounded-lg font-bold hover:bg-purple-800 transition-colors flex justify-center items-center space-x-2 disabled:bg-purple-400"
        >
          {isLoading ? (
            <>
              <Loader2 className="animate-spin" />
              <span>Adjudicating Claim...</span>
            </>
          ) : (
            <span>Submit Claim</span>
          )}
        </button>
      </form>
    </div>
  );
};

export default SubmitClaim;