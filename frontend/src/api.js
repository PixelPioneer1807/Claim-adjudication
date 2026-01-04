import axios from 'axios';

// Connect to your FastAPI backend
const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'multipart/form-data', // Default for file uploads
  },
});

// Helper to handle API errors cleanly
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const submitClaim = async (formData) => {
  return await api.post('/claims/submit', formData);
};

export const getClaimHistory = async () => {
  return await api.get('/claims/history');
};

export const getClaimDetails = async (claimId) => {
  return await api.get(`/claims/${claimId}`);
};

export default api;