import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ShieldCheck, History, PlusCircle } from 'lucide-react';

const Navbar = () => {
  const location = useLocation();

  const isActive = (path) => 
    location.pathname === path ? "bg-purple-700 text-white" : "text-purple-100 hover:bg-purple-600";

  return (
    <nav className="bg-purple-800 shadow-lg">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          {/* Logo Section */}
          <Link to="/" className="flex items-center space-x-2">
            <ShieldCheck className="h-8 w-8 text-white" />
            <span className="text-xl font-bold text-white tracking-wide">
              OPD Adjudicator
            </span>
          </Link>

          {/* Navigation Links */}
          <div className="flex space-x-4">
            <Link
              to="/"
              className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors ${isActive('/')}`}
            >
              <PlusCircle size={18} />
              <span>New Claim</span>
            </Link>
            
            <Link
              to="/history"
              className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors ${isActive('/history')}`}
            >
              <History size={18} />
              <span>History</span>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;