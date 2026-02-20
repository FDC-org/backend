# Accessing DRS PDFs

This document explains how to access Delivery Run Sheet (DRS) PDFs via the backend API.

## API Endpoints

The backend provides two main endpoints for accessing DRS PDFs. These endpoints generate the PDF on-the-fly using the latest data from the database.

### 1. View DRS PDF (Inline)

Use this endpoint to open the PDF directly in the browser (e.g., in a new tab or iframe).

**Endpoint:**
`GET /api/drs/view/<drs_number>/`

**Example:**
`http://<your-domain>/api/drs/view/DRS12345/`

**Response:**
-   **Success (200 OK):** Returns the PDF file with `Content-Disposition: inline`. This tells the browser to display the PDF.
-   **Error:** If the DRS number is invalid or data is missing, it returns an error PDF or a JSON error message.

### 2. Download DRS PDF (Attachment)

Use this endpoint to force a file download of the PDF.

**Endpoint:**
`GET /api/drs/download/<drs_number>/`

**Example:**
`http://<your-domain>/api/drs/download/DRS12345/`

**Response:**
-   **Success (200 OK):** Returns the PDF file with `Content-Disposition: attachment; filename="DRS_<drs_number>.pdf"`. This forces the browser to download the file.

## Frontend Usage

To link to these PDFs from the frontend, simply use a standard anchor tag or open the URL programmatically.

### Example: View Button (React)

```jsx
const viewDrsPdf = (drsNumber) => {
  // Construct absolute URL if needed, or relative if on same domain
  const url = `/api/drs/view/${drsNumber}/`;
  window.open(url, '_blank');
};

<button onClick={() => viewDrsPdf(currentDrsNumber)}>
  View DRS PDF
</button>
```

### Example: Download Button (React)

```jsx
const downloadDrsPdf = (drsNumber) => {
  const url = `/api/drs/download/${drsNumber}/`;
  // Trigger download
  const link = document.createElement('a');
  link.href = url;
  link.download = `DRS_${drsNumber}.pdf`; 
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

<button onClick={() => downloadDrsPdf(currentDrsNumber)}>
  Download DRS PDF
</button>
```

## Potential Issues

If updates "are not working" (i.e., the PDF shows old data):
- Since the PDF is generated on-the-fly, it always reflects the current state of the database at the moment of the request.
- Ensure that the frontend is actually making a new request to the server and not serving a cached version. Adding a timestamp query parameter (e.g., `?t=${Date.now()}`) to the URL can prevent browser caching.

**Example with Cache Busting:**
`GET /api/drs/view/<drs_number>/?t=1678901234`
