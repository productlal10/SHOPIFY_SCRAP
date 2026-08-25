import React, { useState, useEffect } from 'react';
import { fetchProducts, scrapeSingleProduct, bulkScrapeProducts, getExportExcelUrl, getExportCsvUrl } from './services/api';
import './index.css';

export default function App() {
  const [products, setProducts] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [platformFilter, setPlatformFilter] = useState('');
  const [availableFilter, setAvailableFilter] = useState('');
  const [scrapeUrlInput, setScrapeUrlInput] = useState('');
  const [scrapingStatus, setScrapingStatus] = useState(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (platformFilter) params.platform = platformFilter;
      if (availableFilter !== '') params.available = availableFilter === 'true';

      const data = await fetchProducts(params);
      setProducts(data.products || []);
      setTotalCount(data.total || 0);
    } catch (err) {
      console.error('Failed to load products:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [search, platformFilter, availableFilter]);

  const handleScrape = async () => {
    if (!scrapeUrlInput.trim()) return;
    setScrapingStatus('Scraping product data across platform...');
    try {
      const input = scrapeUrlInput.strip ? scrapeUrlInput.strip() : scrapeUrlInput.trim();
      if (input.includes('\n')) {
        const urls = input.split('\n').map(u => u.trim()).filter(Boolean);
        await bulkScrapeProducts(urls);
      } else {
        await scrapeSingleProduct(input);
      }
      setScrapingStatus('✓ Successfully scraped and updated database!');
      setScrapeUrlInput('');
      loadData();
    } catch (err) {
      setScrapingStatus(`❌ Scrape error: ${err.response?.data?.detail || err.message}`);
    }
  };

  const inStockCount = products.filter(p => p.available).length;
  const outStockCount = products.filter(p => !p.available).length;

  return (
    <div className="app-container">
      {/* Header Navbar */}
      <header className="header">
        <div className="logo-group">
          <div className="logo-icon">UE</div>
          <h1 className="logo-title">Universal E-Commerce Inventory Monitor</h1>
        </div>
        <div className="nav-links">
          <a href={getExportExcelUrl()} download className="btn-secondary" style={{ textDecoration: 'none' }}>
            📥 Export Excel (.xlsx)
          </a>
          <a href={getExportCsvUrl()} download className="btn-secondary" style={{ textDecoration: 'none' }}>
            📄 Export CSV
          </a>
        </div>
      </header>

      {/* Main Content Dashboard */}
      <main className="main-content">
        {/* Metric Cards Grid */}
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-label">Total Monitored Products</span>
            <span className="metric-value">{totalCount}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">In Stock Items</span>
            <span className="metric-value" style={{ color: 'var(--accent-emerald)' }}>{inStockCount}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Out of Stock Items</span>
            <span className="metric-value" style={{ color: 'var(--accent-rose)' }}>{outStockCount}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Supported Platforms</span>
            <span className="metric-value" style={{ color: 'var(--accent-blue)' }}>4 (Shopify, Myntra, Flipkart, Amazon)</span>
          </div>
        </div>

        {/* Scrape Input Section */}
        <div className="controls-bar" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <input
              type="text"
              placeholder="Paste Product URL to Scrape (e.g. Shopify, Myntra, Flipkart, Amazon India)..."
              className="search-input"
              style={{ flex: 1 }}
              value={scrapeUrlInput}
              onChange={(e) => setScrapeUrlInput(e.target.value)}
            />
            <button className="btn-primary" onClick={handleScrape}>
              🔍 Scrape & Monitor
            </button>
          </div>
          {scrapingStatus && (
            <div style={{ fontSize: '0.875rem', color: scrapingStatus.startsWith('✓') ? 'var(--accent-emerald)' : 'var(--accent-blue)', marginTop: '0.5rem' }}>
              {scrapingStatus}
            </div>
          )}
        </div>

        {/* Filter Controls Bar */}
        <div className="controls-bar">
          <input
            type="text"
            placeholder="Search product title, brand, or SKU..."
            className="search-input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <div style={{ display: 'flex', gap: '1rem' }}>
            <select
              className="select-filter"
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
            >
              <option value="">All Platforms</option>
              <option value="shopify">Shopify</option>
              <option value="myntra">Myntra</option>
              <option value="flipkart">Flipkart</option>
              <option value="amazon">Amazon India</option>
            </select>

            <select
              className="select-filter"
              value={availableFilter}
              onChange={(e) => setAvailableFilter(e.target.value)}
            >
              <option value="">All Availability</option>
              <option value="true">In Stock Only</option>
              <option value="false">Out of Stock Only</option>
            </select>

            <button className="btn-secondary" onClick={loadData}>
              🔄 Refresh
            </button>
          </div>
        </div>

        {/* Products Data Table */}
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Platform</th>
                <th>Brand</th>
                <th>Product Name</th>
                <th>Selling Price</th>
                <th>MRP</th>
                <th>Discount</th>
                <th>Stock Status</th>
                <th>Exact Stock</th>
                <th>Stock Source</th>
                <th>URL</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="10" style={{ textAlign: 'center', padding: '2rem' }}>Loading monitored catalog data...</td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan="10" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                    No products found. Paste a product URL above to start monitoring!
                  </td>
                </tr>
              ) : (
                products.map((p) => (
                  <tr key={p.id || p.product_id}>
                    <td>
                      <span className="badge badge-platform">{p.platform}</span>
                    </td>
                    <td><strong>{p.brand}</strong></td>
                    <td style={{ maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {p.product_name}
                    </td>
                    <td><strong>₹{p.selling_price?.toLocaleString() || 'N/A'}</strong></td>
                    <td style={{ textDecoration: 'line-through', color: 'var(--text-secondary)' }}>
                      ₹{p.mrp?.toLocaleString() || 'N/A'}
                    </td>
                    <td>
                      {p.discount_percent > 0 ? (
                        <span style={{ color: 'var(--accent-emerald)', fontWeight: '600' }}>
                          {p.discount_percent}% OFF
                        </span>
                      ) : '-'}
                    </td>
                    <td>
                      <span className={`badge ${p.available ? 'badge-in-stock' : 'badge-out-stock'}`}>
                        {p.stock_status || (p.available ? 'IN_STOCK' : 'OUT_OF_STOCK')}
                      </span>
                    </td>
                    <td>
                      {p.exact_stock !== null ? (
                        <strong style={{ color: 'var(--accent-blue)' }}>{p.exact_stock} units</strong>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>NULL</span>
                      )}
                    </td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      {p.stock_source || 'not_publicly_available'}
                    </td>
                    <td>
                      <a
                        href={p.product_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: 'var(--accent-blue)', textDecoration: 'none' }}
                      >
                        Link ↗
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
