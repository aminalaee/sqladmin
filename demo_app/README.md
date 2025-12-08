# SQLAdmin Demo Application

This demo application showcases **ALL** new features added in this PR:

## 🎯 Features Demonstrated

### 1. **UniqueValuesFilter**
- ✅ Integer columns (User.age)
- ✅ Float columns with custom formatting (User.salary - displays as $75,000.00)
- ✅ Custom rounding (Salary rounded to $10k increments)
- ✅ Custom ordering

### 2. **ManyToManyFilter**
- ✅ Filter Users by Roles through user_roles junction table
- ✅ Filter Products by Tags through product_tags junction table

### 3. **RelatedModelFilter**
- ✅ Filter Orders by Customer's Department (through User relationship)

### 4. **DateRangeFilter**
- ✅ Filter Users by Registration Date
- ✅ Filter Orders by Order Date
- ✅ Filter Orders by Shipped Date
- ✅ Filter Products by Created Date
- ✅ Interactive datetime-local inputs in UI

### 5. **Enhanced ForeignKeyFilter**
- ✅ Multiple value selection
- ✅ Custom ordering (Department, Category sorted alphabetically)

### 6. **Pretty Export**
- ✅ CSV export with column labels and formatters
- ✅ JSON export with column labels and formatters
- ✅ Custom formatters applied (salary as $XX,XXX.XX)

### 7. **Query Optimization**
- ✅ `_safe_join()` - prevents duplicate JOINs
- ✅ `add_relation_loads()` - eliminates N+1 queries
- ✅ Search with related models (e.g., search orders by user name)

### 8. **Additional Features**
- ✅ Read-only views (Order Reports)
- ✅ Custom actions (Activate Users)
- ✅ Related field display (department.name, user.name)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd demo_app

# Install sqladmin from parent directory
pip install -e ..

# Install demo dependencies
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python main.py
```

### 3. Open Admin Interface

Navigate to: **http://localhost:8000/admin**

## 📋 What to Test

### UniqueValuesFilter

1. Go to **Users**
2. In the Filters sidebar, click on **Age** or **Salary**
3. Select multiple values (e.g., age 28 and 35)
4. Notice salary displays as "$75,000.00" with proper formatting

### ManyToManyFilter

1. Go to **Users**
2. Filter by **Role**
3. Select "Admin" or "Manager" to see users with those roles
4. Users can have multiple roles (many-to-many)

### RelatedModelFilter

1. Go to **Orders**
2. Filter by **Customer Department**
3. See orders filtered by the department of the customer who placed them
4. Notice automatic JOIN to User → Department

### DateRangeFilter

1. Go to **Users**, **Orders**, or **Products**
2. Find **Date Range** filters (Registration Date, Order Date, etc.)
3. Click to open the date picker
4. Select start date, end date, or both
5. Click Apply to filter

### Multiple Selection

1. Any filter (except DateRange and Operation filters) supports multiple selection
2. Select multiple values and click Apply
3. Results will include records matching ANY of the selected values (OR logic)

### Pretty Export

1. Go to any list view
2. Click **Export** dropdown (top right)
3. Choose **CSV** or **JSON**
4. Downloaded file will have:
   - Column labels (not database column names)
   - Formatted values ($75,000.00 instead of 75000.5)
   - Related field names (Department instead of department_id)

### Custom Actions

1. Go to **Users** list
2. Select some users (checkboxes)
3. Click **Actions** → **Activate Selected Users**
4. Confirm the action

### Read-Only View

1. Go to **Order Reports** (in sidebar)
2. Notice no Create/Edit/Delete buttons
3. Can still filter and export

## 📊 Sample Data

The database is initialized with:
- **4 Users** (various ages, salaries, departments)
- **3 Departments** (IT, HR, Sales)
- **3 Roles** (Admin, User, Manager)
- **4 Products** (various prices, stock levels)
- **3 Categories** (Electronics, Books, Clothing)
- **3 Tags** (New, Sale, Popular)
- **3 Orders** (different statuses and dates)

## 🧪 Testing Scenarios

### Scenario 1: E-commerce Filtering
1. Go to **Products**
2. Filter by:
   - Category: "Electronics"
   - Tags: "Popular"
   - Price Range: "$1,299.99"
   - Available: "Yes"
3. Export as CSV

### Scenario 2: HR Reports
1. Go to **Users**
2. Filter by:
   - Department: "IT"
   - Salary: "$75,000.00" or "$85,000.00"
   - Active: "Yes"
   - Registration Date: from 2024-01-01 to 2024-06-30
3. Export as JSON

### Scenario 3: Order Analytics
1. Go to **Orders**
2. Filter by:
   - Customer Department: "Sales"
   - Order Date: from 2024-08-01 to 2024-12-31
   - Status: "processing" or "pending"
3. View related items

### Scenario 4: Read-Only Reporting
1. Go to **Order Reports**
2. Filter by date range
3. Export data
4. Notice no edit/delete options

## 🎨 UI Features

- **Filter Sidebar** - All filters in a dedicated sidebar
- **Search Filters** - Search within filter options (for lists > 10 items)
- **Visual Indicators** - Filled icon when filter is active
- **Clear Buttons** - Easy to clear individual filters
- **Multiple Selection** - Checkboxes for selecting multiple filter values
- **Date Pickers** - Native datetime-local inputs
- **Responsive Design** - Works on different screen sizes

## 🔧 Troubleshooting

### Database locked error
```bash
rm demo.db
python main.py
```

### Import errors
```bash
# Make sure you installed sqladmin from parent directory
pip install -e ..
```

### Port already in use
Edit `main.py` and change port from 8000 to something else.

## 📝 Notes

- Database file: `demo.db` (created automatically)
- Sample data is created on first run
- Press Ctrl+C to stop the server
- Use `reload=True` for development

## 🎓 Learning Resources

After testing the demo, check out the documentation:
- `docs/cookbook/advanced_filtering.md` - Detailed filtering guide
- `docs/cookbook/readonly_views.md` - Read-only view patterns
- `docs/configurations.md` - All configuration options

---

**Enjoy exploring SQLAdmin's new features! 🚀**

