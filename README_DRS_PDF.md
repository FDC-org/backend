# Accessing DRS PDFs

This document explains how to access Delivery Run Sheet (DRS) PDFs via the backend API.

## Overview

The backend provides specific endpoints to generate and serve DRS PDFs on-the-fly. These endpoints do not require authentication token in the header, making them easy to use for direct download links or inline viewing in the frontend.

## API Endpoints

### 1. View DRS PDF (Inline)

Use this endpoint to open the PDF in the browser (e.g., in a new tab or iframe).

**Endpoint:**
`GET /api/drs/view/<drs_number>/`

**Example:**
http://localhost:8000/api/drs/view/12345/

**Response:**
-   **Success (200 OK):** Returns the PDF file with `Content-Disposition: inline`.
-   **Not Found (404/200):** If the DRS is not found or data is missing, it may return a specialized "Error PDF" explaining the issue, or a JSON 404 error if configured. Currently, it generates an Error PDF.

### 2. Download DRS PDF (Attachment)

Use this endpoint to trigger a file download.

**Endpoint:**
`GET /api/drs/download/<drs_number>/`

**Example:**
http://localhost:8000/api/drs/download/12345/

**Response:**
-   **Success (200 OK):** Returns the PDF file with `Content-Disposition: attachment; filename="DRS_<drs_number>.pdf"`.

## Frontend Integration Guide

To invoke these from the frontend (e.g., React, plain HTML):

```javascript
// Example: Function to open DRS PDF in new tab
const openDrsPdf = (drsNumber) => {
  const url = `${API_BASE_URL}/api/drs/view/${drsNumber}/`;
  window.open(url, '_blank');
};

// Example: Function to download DRS PDF
const downloadDrsPdf = (drsNumber) => {
  const url = `${API_BASE_URL}/api/drs/download/${drsNumber}/`;
  // Create a temporary link to trigger download
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `DRS_${drsNumber}.pdf`); // Optional, backend sets filename usually
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
```

## Troubleshooting

-   **"Details not found" / Error PDF**: This usually means the `drs_number` provided in the URL does not exist in the `DRS` table, or associated data (Branch, User, etc.) is missing. Check the backend logs for `Error gathering DRS data`.
-   **404 Not Found**: Ensure the URL path is exactly `/api/drs/view/...` or `/api/drs/download/...`. 
