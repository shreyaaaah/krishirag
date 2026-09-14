import React, { useState, useEffect } from 'react';
import { ShoppingBag, Search, RefreshCw, TrendingUp, Filter } from 'lucide-react';
import { fetchMandiPrices } from '../api/client';

export default function MandiPriceWidget() {
  const [filters, setFilters] = useState({
    state: 'Punjab',
    district: '',
    commodity: '',
  });
  const [data, setData] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadPrices = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchMandiPrices(filters);
      setData(res.data || []);
      setTotalCount(res.total || 0);
    } catch (err) {
      setError(err.message || 'Failed to load mandi prices.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPrices();
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    loadPrices();
  };

  const setPreset = (commodityName) => {
    const updated = { ...filters, commodity: commodityName };
    setFilters(updated);
    fetchMandiPrices(updated).then((res) => {
      setData(res.data || []);
      setTotalCount(res.total || 0);
    });
  };

  return (
    <div className="flex flex-col h-full bg-slate-950/40 rounded-2xl border border-emerald-900/40 shadow-2xl backdrop-blur-sm overflow-hidden">
      {/* Header */}
      <div className="bg-emerald-950/80 px-5 py-4 border-b border-emerald-800/40 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-500/20 rounded-xl border border-amber-500/30 text-amber-400">
            <ShoppingBag className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-emerald-100 text-base">Live Mandi Prices</h3>
            <p className="text-xs text-emerald-400/80">Real-Time Market Rate Lookup</p>
          </div>
        </div>
        <button
          onClick={loadPrices}
          disabled={isLoading}
          className="p-2 rounded-lg bg-emerald-900/40 hover:bg-emerald-800/60 text-emerald-300 transition-colors disabled:opacity-50"
          title="Refresh Prices"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Filter Form */}
      <form onSubmit={handleSearch} className="p-4 bg-emerald-950/40 border-b border-emerald-900/40 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          <div>
            <label className="block text-[11px] font-medium text-emerald-400 mb-1">State</label>
            <input
              type="text"
              value={filters.state}
              onChange={(e) => setFilters({ ...filters, state: e.target.value })}
              placeholder="e.g. Punjab"
              className="w-full bg-slate-900/80 border border-emerald-800/60 rounded-xl px-3 py-1.5 text-xs text-emerald-100 placeholder-emerald-600 outline-none focus:border-emerald-400"
            />
          </div>
          <div>
            <label className="block text-[11px] font-medium text-emerald-400 mb-1">District</label>
            <input
              type="text"
              value={filters.district}
              onChange={(e) => setFilters({ ...filters, district: e.target.value })}
              placeholder="e.g. Jalandhar"
              className="w-full bg-slate-900/80 border border-emerald-800/60 rounded-xl px-3 py-1.5 text-xs text-emerald-100 placeholder-emerald-600 outline-none focus:border-emerald-400"
            />
          </div>
          <div>
            <label className="block text-[11px] font-medium text-emerald-400 mb-1">Commodity</label>
            <input
              type="text"
              value={filters.commodity}
              onChange={(e) => setFilters({ ...filters, commodity: e.target.value })}
              placeholder="e.g. Wheat, Rice"
              className="w-full bg-slate-900/80 border border-emerald-800/60 rounded-xl px-3 py-1.5 text-xs text-emerald-100 placeholder-emerald-600 outline-none focus:border-emerald-400"
            />
          </div>
        </div>

        {/* Quick commodity preset chips */}
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-1.5 overflow-x-auto py-1">
            <span className="text-[11px] text-emerald-500 font-medium flex items-center gap-1">
              <Filter className="w-3 h-3" /> Quick:
            </span>
            {['Wheat', 'Rice', 'Cotton', 'Maize'].map((c) => (
              <button
                type="button"
                key={c}
                onClick={() => setPreset(c)}
                className="text-[11px] bg-emerald-900/40 hover:bg-emerald-800/60 text-emerald-200 border border-emerald-700/40 px-2 py-0.5 rounded-lg transition-colors"
              >
                {c}
              </button>
            ))}
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-3 py-1.5 rounded-xl font-medium flex items-center gap-1 transition-all shrink-0"
          >
            <Search className="w-3.5 h-3.5" />
            Filter
          </button>
        </div>
      </form>

      {/* Table Data Area */}
      <div className="flex-1 overflow-y-auto p-3">
        {isLoading ? (
          <div className="h-40 flex items-center justify-center text-xs text-emerald-400 gap-2">
            <RefreshCw className="w-4 h-4 animate-spin" /> Loading mandi records...
          </div>
        ) : error ? (
          <div className="p-4 bg-rose-950/40 border border-rose-800/50 rounded-xl text-xs text-rose-300 text-center">
            {error}
          </div>
        ) : data.length === 0 ? (
          <div className="h-40 flex items-center justify-center text-xs text-emerald-500/70 text-center">
            No mandi records found for the selected filters.
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center justify-between px-1 text-[11px] text-emerald-400/80 font-medium">
              <span>Showing {data.length} records</span>
              <span className="flex items-center gap-1"><TrendingUp className="w-3 h-3 text-emerald-400" /> ₹ / Quintal</span>
            </div>

            <div className="border border-emerald-900/50 rounded-xl overflow-hidden shadow-inner">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-emerald-950/90 text-emerald-300 border-b border-emerald-800/40 text-[11px]">
                    <th className="p-2.5">Market</th>
                    <th className="p-2.5">Commodity</th>
                    <th className="p-2.5 text-right">Min</th>
                    <th className="p-2.5 text-right">Max</th>
                    <th className="p-2.5 text-right font-semibold text-emerald-200">Modal</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-emerald-900/30">
                  {data.map((row) => (
                    <tr key={row.id} className="hover:bg-emerald-900/30 transition-colors">
                      <td className="p-2.5 font-medium text-emerald-100">
                        {row.market}
                        <span className="block text-[10px] text-emerald-500 font-normal">{row.district}, {row.state}</span>
                      </td>
                      <td className="p-2.5 text-emerald-200">
                        {row.commodity}
                        <span className="block text-[10px] text-emerald-500">{row.variety || 'Local'}</span>
                      </td>
                      <td className="p-2.5 text-right text-emerald-400/90">₹{row.min_price || '-'}</td>
                      <td className="p-2.5 text-right text-emerald-400/90">₹{row.max_price || '-'}</td>
                      <td className="p-2.5 text-right font-semibold text-emerald-300">
                        ₹{row.modal_price || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
