import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export const fetchProducts = async (params = {}) => {
  const response = await axios.get(`${API_BASE_URL}/products`, { params });
  return response.data;
};

export const scrapeSingleProduct = async (url) => {
  const response = await axios.post(`${API_BASE_URL}/products/scrape`, { url });
  return response.data;
};

export const bulkScrapeProducts = async (urls) => {
  const response = await axios.post(`${API_BASE_URL}/products/bulk-scrape`, { urls });
  return response.data;
};

export const fetchProductDetails = async (id) => {
  const response = await axios.get(`${API_BASE_URL}/products/${id}`);
  return response.data;
};

export const fetchProductHistory = async (id) => {
  const response = await axios.get(`${API_BASE_URL}/products/${id}/history`);
  return response.data;
};

export const getExportExcelUrl = () => `${API_BASE_URL}/export/excel`;
export const getExportCsvUrl = () => `${API_BASE_URL}/export/csv`;
