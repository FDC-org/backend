```
### 1. DRS Creation (POST) - Updated Response

**Endpoint:** `POST /api/drs/`

**New Response Format:**
```json
{
  "status": "success",
  "drs_number": "251333610159",
  "document_url": null 
}
```

**Changes:**
- `document_url` is now `null` (PDF is generated on-demand)
- Use the download endpoint to get the PDF

### 2. DRS List (GET) - Updated Response

**Endpoint:** `GET /api/drs/{date}`

**Example:** `GET /api/drs/2026-02-15`

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "date": "2026-02-15T12:10:00",
      "drsno": "251333610159",
      "boy": "SASTRY",
      "location": "GT ROAD",
      "awbdata": [...],
      "document_url": null
    }
  ]
}
```

### 3. PDF Download & View Endpoints (UNCHANGED)

**Download:** `GET /api/drs/download/{drs_number}/`
**View Inline:** `GET /api/drs/view/{drs_number}/`

These endpoints now generate the PDF on-the-fly. No cloud storage is used.
```