import React, { useRef, useState } from 'react';
import { importCSV } from '../api.js';

/**
 * ImportCSV
 * Two broker-specific file upload buttons. On file select, uploads to POST /api/import.
 * Shows uploading/success/error states per UI-SPEC copywriting contract.
 */
export default function ImportCSV({ onImportSuccess }) {
  const zerodhaRef = useRef(null);
  const trRef = useRef(null);

  const [zerodhaStatus, setZerodhaStatus] = useState(null); // null | 'uploading' | {count} | {error}
  const [trStatus, setTrStatus] = useState(null);

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

  function renderStatus(status, broker) {
    if (!status) return null;
    if (status.uploading) {
      return <span className="import-status import-status--uploading">Uploading...</span>;
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
          CSV upload failed — {status.error}. Please check file format and try again.
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
        {renderStatus(zerodhaStatus, 'zerodha')}
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
        {renderStatus(trStatus, 'trade_republic')}
      </div>
    </div>
  );
}
