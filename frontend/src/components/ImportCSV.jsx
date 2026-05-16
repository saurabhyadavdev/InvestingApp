import React, { useRef, useState } from 'react';
import { importCSV } from '../api.js';

/**
 * ImportCSV
 * Broker-specific file upload buttons for Zerodha (CSV), Trade Republic (CSV),
 * and Traders Place (PDF quarterly statement).
 */
export default function ImportCSV({ onImportSuccess }) {
  const zerodhaRef = useRef(null);
  const trRef = useRef(null);
  const tpRef = useRef(null);

  const [zerodhaStatus, setZerodhaStatus] = useState(null);
  const [trStatus, setTrStatus] = useState(null);
  const [tpStatus, setTpStatus] = useState(null);

  async function handleFileSelect(broker, file, setStatus) {
    if (!file) return;
    setStatus({ uploading: true });
    try {
      const result = await importCSV(broker, file);
      setStatus({ count: result.imported_count });
      if (onImportSuccess) onImportSuccess();
    } catch (err) {
      setStatus({ error: err.message || 'Unknown error' });
    }
  }

  function renderStatus(status, isPdf) {
    if (!status) return null;
    if (status.uploading) {
      return <span className="import-status import-status--uploading">{isPdf ? 'Parsing PDF…' : 'Uploading…'}</span>;
    }
    if (status.count !== undefined) {
      return (
        <span className="import-status import-status--success">
          Imported {status.count} holdings
        </span>
      );
    }
    if (status.error) {
      return (
        <span className="import-status import-status--error">
          Upload failed — {status.error}. Check format and retry.
        </span>
      );
    }
    return null;
  }

  return (
    <div className="import-csv-section">
      <div className="import-csv-row">
        <button
          className="btn-import"
          onClick={() => zerodhaRef.current && zerodhaRef.current.click()}
          disabled={zerodhaStatus?.uploading}
        >
          Import Zerodha CSV
        </button>
        <input
          ref={zerodhaRef}
          type="file"
          accept=".csv,text/csv"
          style={{ display: 'none' }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = '';
            handleFileSelect('zerodha', file, setZerodhaStatus);
          }}
        />
        {renderStatus(zerodhaStatus, false)}
      </div>

      <div className="import-csv-row">
        <button
          className="btn-import"
          onClick={() => trRef.current && trRef.current.click()}
          disabled={trStatus?.uploading}
        >
          Import Trade Republic CSV
        </button>
        <input
          ref={trRef}
          type="file"
          accept=".csv,text/csv"
          style={{ display: 'none' }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = '';
            handleFileSelect('trade_republic', file, setTrStatus);
          }}
        />
        {renderStatus(trStatus, false)}
      </div>

      <div className="import-csv-row">
        <button
          className="btn-import"
          onClick={() => tpRef.current && tpRef.current.click()}
          disabled={tpStatus?.uploading}
        >
          Import Traders Place PDF
        </button>
        <input
          ref={tpRef}
          type="file"
          accept=".pdf,application/pdf"
          style={{ display: 'none' }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = '';
            handleFileSelect('traders_place', file, setTpStatus);
          }}
        />
        {renderStatus(tpStatus, true)}
      </div>
    </div>
  );
}
