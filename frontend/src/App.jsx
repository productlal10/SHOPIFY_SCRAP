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
  const [expandedRows, setExpandedRows] = useState({});

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

  const toggleExpand = (id) => {
    setExpandedRows(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleScrape = async () => {
    if (!scrapeUrlInput.trim()) return;
    setScrapingStatus('Scraping product & size variant data across platform...');
    try {
      const input = scrapeUrlInput.trim();
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
              placeholder="Paste Product URL to Scrape (Shopify, Myntra, Flipkart, Amazon India)..."
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
                <th>Size Variants Breakdown</th>
                <th>Selling Price</th>
                <th>MRP</th>
                <th>Discount</th>
                <th>Total Stock</th>
                <th>Stock Source</th>
                <th>Action</th>
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
                products.map((p) => {
                  const pid = p.id || p.product_id;
                  const isExpanded = expandedRows[pid];
                  const hasVariants = p.variants && p.variants.length > 0;

                  return (
                    <React.Fragment key={pid}>
                      <tr>
                        <td>
                          <span className="badge badge-platform">{p.platform}</span>
                        </td>
                        <td><strong>{p.brand}</strong></td>
                        <td style={{ maxWidth: '280px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          <a href={p.product_url} target="_blank" rel="noreferrer" style={{ color: 'var(--text-primary)', textDecoration: 'none' }}>
                            {p.product_name} ↗
                          </a>
                        </td>
                        <td>
                          {hasVariants ? (
                            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                              {p.variants.slice(0, 5).map((v, i) => (
                                <span
                                  key={i}
                                  style={{
                                    fontSize: '0.75rem',
                                    padding: '0.15rem 0.4rem',
                                    borderRadius: '4px',
                                    background: v.available ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                                    color: v.available ? 'var(--accent-emerald)' : 'var(--accent-rose)',
                                    border: '1px solid rgba(255,255,255,0.1)'
                                  }}
                                >
                                  {v.size || 'Default'}: {v.exact_stock !== null ? `${v.exact_stock}u` : (v.available ? 'In Stock' : 'Out')}
                                </span>
                              ))}
                              {p.variants.length > 5 && (
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                  +{p.variants.length - 5} more
                                </span>
                              )}
                            </div>
                          ) : (
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>No size breakdown</span>
                          )}
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
                          {p.exact_stock !== null ? (
                            <strong style={{ color: 'var(--accent-blue)' }}>{p.exact_stock} units</strong>
                          ) : (
                            <span className={`badge ${p.available ? 'badge-in-stock' : 'badge-out-stock'}`}>
                              {p.stock_status || (p.available ? 'IN_STOCK' : 'OUT_OF_STOCK')}
                            </span>
                          )}
                        </td>
                        <td style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          {p.stock_source || 'not_publicly_available'}
                        </td>
                        <td>
                          {hasVariants && (
                            <button
                              className="btn-secondary"
                              style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                              onClick={() => toggleExpand(pid)}
                            >
                              {isExpanded ? 'Hide Sizes ▲' : 'View Sizes ▼'}
                            </button>
                          )}
                        </td>
                      </tr>

                      {/* Expanded Size Variants Row */}
                      {isExpanded && hasVariants && (
                        <tr style={{ background: 'rgba(15, 23, 42, 0.4)' }}>
                          <td colSpan="10" style={{ padding: '1rem 2rem' }}>
                            <div style={{ fontSize: '0.85rem', fontWeight: '600', marginBottom: '0.5rem', color: 'var(--accent-blue)' }}>
                              📐 Size & Color Variant Breakdown for {p.product_name}:
                            </div>
                            <table style={{ width: '100%', background: 'rgba(30, 41, 59, 0.5)', borderRadius: '8px' }}>
                              <thead>
                                <tr style={{ fontSize: '0.75rem' }}>
                                  <th>Variant ID</th>
                                  <th>SKU</th>
                                  <th>Size</th>
                                  <th>Color</th>
                                  <th>Variant Price</th>
                                  <th>MRP</th>
                                  <th>Availability</th>
                                  <th>Exact Stock Left</th>
                                  <th>Stock Source</th>
                                </tr>
                              </thead>
                              <tbody>
                                {p.variants.map((v, idx) => (
                                  <tr key={idx} style={{ fontSize: '0.8rem' }}>
                                    <td>{v.variant_id}</td>
                                    <td>{v.sku || '-'}</td>
                                    <td><strong>{v.size || 'Default'}</strong></td>
                                    <td>{v.color || '-'}</td>
                                    <td><strong>₹{v.selling_price?.toLocaleString() || p.selling_price}</strong></td>
                                    <td style={{ textDecoration: 'line-through', color: 'var(--text-secondary)' }}>
                                      ₹{v.mrp?.toLocaleString() || p.mrp}
                                    </td>
                                    <td>
                                      <span className={`badge ${v.available ? 'badge-in-stock' : 'badge-out-stock'}`}>
                                        {v.stock_status || (v.available ? 'IN_STOCK' : 'OUT_OF_STOCK')}
                                      </span>
                                    </td>
                                    <td>
                                      {v.exact_stock !== null ? (
                                        <strong style={{ color: 'var(--accent-blue)' }}>{v.exact_stock} units</strong>
                                      ) : (
                                        <span style={{ color: 'var(--text-secondary)' }}>NULL</span>
                                      )}
                                    </td>
                                    <td style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                      {v.stock_source || p.stock_source}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
