# Multi-Tenant Company Branding - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### Step 1: Add Cloudinary Credentials

Edit your `.env` file and add:

```env
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

Get these from: https://cloudinary.com/console

---

### Step 2: Create Your First Company

**Using Django Admin (Easiest):**

1. Start server: `python manage.py runserver`
2. Go to: http://localhost:8000/admin
3. Navigate to "Company Profiles"
4. Click "Add Company Profile"
5. Fill in:
   - **Company Code**: `FDC001` (unique identifier)
   - **Company Name**: `Your Company Name`
   - **Primary Color**: `#2196F3` (hex color)
   - **Secondary Color**: `#1976D2`
   - **Contact Email**: `info@yourcompany.com`
6. Click "Save"

**Using Django Shell (Alternative):**

```bash
python manage.py shell
```

```python
from api.models import CompanyProfile

company = CompanyProfile.objects.create(
    company_code='FDC001',
    company_name='Your Company Name',
    primary_color='#2196F3',
    secondary_color='#1976D2',
    contact_email='info@yourcompany.com',
    is_active=True
)
print(f"Created: {company}")
```

---

### Step 3: Assign Users to Company

**Using Django Shell:**

```bash
python manage.py shell
```

```python
from api.models import UserDetails, CompanyProfile

# Get the company
company = CompanyProfile.objects.get(company_code='FDC001')

# Assign a specific user
user = UserDetails.objects.get(user__username='your_username')
user.company = company
user.save()

print(f"Assigned {user.fullname()} to {company.company_name}")
```

---

### Step 4: Upload Company Logo

**Using cURL:**

```bash
# First, login to get token
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}'

# Copy the token from response, then upload logo
curl -X POST http://localhost:8000/api/company/logo/ \
  -H "Authorization: Token YOUR_TOKEN_HERE" \
  -F "logo=@/path/to/your/logo.png"
```

**Using Postman:**
1. POST to `http://localhost:8000/api/company/logo/`
2. Headers: `Authorization: Token YOUR_TOKEN`
3. Body → form-data → key: `logo`, value: select image file
4. Send

---

### Step 5: Test Login

**Test the API:**

```bash
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}'
```

**Expected Response:**

```json
{
  "token": "your-auth-token",
  "company": {
    "company_code": "FDC001",
    "company_name": "Your Company Name",
    "logo_url": "https://res.cloudinary.com/.../logo.png",
    "primary_color": "#2196F3",
    "secondary_color": "#1976D2"
  }
}
```

✅ If you see the `company` object with your data, **it's working!**

---

## 📱 Frontend Integration

### Update Your Login Code

```javascript
async function login(username, password) {
  const response = await fetch('http://localhost:8000/api/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  
  const data = await response.json();
  
  if (data.company) {
    // Store company data
    localStorage.setItem('company', JSON.stringify(data.company));
    
    // Display logo
    document.getElementById('logo').src = data.company.logo_url;
    
    // Display company name
    document.getElementById('company-name').textContent = data.company.company_name;
  }
}
```

---

## 🎨 Available API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/login/` | POST | Login (returns company data) |
| `/api/company/profile/` | GET | Get your company profile |
| `/api/company/logo/` | POST | Upload company logo |
| `/api/company/update/` | PUT | Update company details |
| `/api/company/list/` | GET | List all companies (admin) |

---

## 🔧 Troubleshooting

**Problem: Login doesn't return company data**
- Check if user is assigned to a company: `UserDetails.objects.get(user__username='username').company`

**Problem: Logo upload fails**
- Verify Cloudinary credentials in `.env`
- Check user has hub/admin permissions

**Problem: Can't see company in admin**
- Run migrations: `python manage.py migrate`
- Restart server

---

## 📚 Full Documentation

For complete documentation, see [walkthrough.md](file:///C:/Users/dharm/.gemini/antigravity/brain/85c071d0-596b-4c65-8638-a41cb6adeb67/walkthrough.md)

---

## ✨ What's Next?

1. **Create multiple companies** for testing
2. **Upload logos** for each company
3. **Update your frontend** to display company branding
4. **Add company filtering** to bookings/deliveries (optional)
5. **Customize colors** per company theme
