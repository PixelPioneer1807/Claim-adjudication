import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import SubmitClaim from './components/SubmitClaim';
import ClaimResult from './components/ClaimResult';
import History from './components/History';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-50 font-sans">
        <Navbar />
        <main className="max-w-6xl mx-auto py-8 px-4">
          <Routes>
            {/* Page 1: Drag & Drop Submission Form */}
            <Route path="/" element={<SubmitClaim />} />
            
            {/* Page 2: Adjudication Result (Approved/Rejected) */}
            <Route path="/result/:claimId" element={<ClaimResult />} />
            
            {/* Page 3: Admin/History View */}
            <Route path="/history" element={<History />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;