# Read-Only Views

This guide shows how to create read-only admin views for viewing data without editing capabilities.

## Overview

Read-only views are useful for:
- Displaying reports and analytics
- Showing aggregated data
- Providing read-only access to sensitive data
- Creating audit logs views

## Basic Read-Only View

The simplest way to create a read-only view is to disable all write operations:

```python
from sqladmin import ModelView

class AuditLogAdmin(ModelView, model=AuditLog):
    # Disable all write operations
    can_create = False
    can_edit = False
    can_delete = False
    
    # Optional: Disable export if needed
    can_export = True
    
    column_list = [
        AuditLog.id,
        AuditLog.user,
        AuditLog.action,
        AuditLog.timestamp,
    ]
```

## Creating a Reusable Read-Only Base Class

For multiple read-only views, create a base class:

```python
from sqladmin import ModelView

class ReadOnlyModelView(ModelView):
    """Base class for read-only views."""
    
    can_create = False
    can_edit = False
    can_delete = False
    can_export = True
    
    # Optional: Use a custom template
    list_template = "sqladmin/list.html"

# Use the base class
class AuditLogAdmin(ReadOnlyModelView, model=AuditLog):
    column_list = [AuditLog.id, AuditLog.action, AuditLog.timestamp]

class SystemLogAdmin(ReadOnlyModelView, model=SystemLog):
    column_list = [SystemLog.id, SystemLog.level, SystemLog.message]
```

## Analytics and Reports View

Create views for aggregated or computed data:

```python
from sqlalchemy import func, select
from sqladmin import ModelView

class SalesReportAdmin(ReadOnlyModelView, model=Order):
    name = "Sales Report"
    name_plural = "Sales Reports"
    
    # Show aggregated columns
    column_list = [
        Order.date,
        Order.customer,
        Order.total_amount,
        Order.status,
    ]
    
    # Add default sorting
    column_default_sort = ("date", True)  # Descending
    
    # Add filters for date range
    column_filters = [
        Order.date,
        Order.status,
        Order.customer_id,
    ]
    
    # Custom search
    column_searchable_list = [Order.customer]
    
    # Custom formatters for display
    column_formatters = {
        Order.total_amount: lambda m, a: f"${m.total_amount:,.2f}",
        Order.date: lambda m, a: m.date.strftime("%Y-%m-%d"),
    }
```

## Adding Custom Context to Read-Only Views

You can add summary statistics or additional context:

```python
from starlette.requests import Request

class OrderReportAdmin(ReadOnlyModelView, model=Order):
    name = "Order Report"
    
    async def perform_list_context(
        self, request: Request, context: dict | None = None
    ) -> dict:
        """Add summary statistics to the view."""
        context = context or {}
        
        # Calculate summary stats
        if self.is_async:
            async with self.session_maker() as session:
                # Total orders
                total_orders = await session.scalar(
                    select(func.count(Order.id))
                )
                # Total revenue
                total_revenue = await session.scalar(
                    select(func.sum(Order.total_amount))
                ) or 0
        else:
            with self.session_maker() as session:
                total_orders = session.scalar(select(func.count(Order.id)))
                total_revenue = session.scalar(
                    select(func.sum(Order.total_amount))
                ) or 0
        
        # Add to context
        context["total_orders"] = total_orders
        context["total_revenue"] = f"${total_revenue:,.2f}"
        
        return context
```

Then create a custom template to display the statistics:

```html title="templates/sqladmin/order_report.html"
{% extends "sqladmin/list.html" %}

{% block content_header %}
    {{ super() }}
    <div class="row mt-3 mb-3">
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5>Total Orders</h5>
                    <h2>{{ total_orders }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5>Total Revenue</h5>
                    <h2>{{ total_revenue }}</h2>
                </div>
            </div>
        </div>
    </div>
{% endblock %}
```

```python
class OrderReportAdmin(ReadOnlyModelView, model=Order):
    list_template = "sqladmin/order_report.html"
    # ... rest of the configuration
```

## Filtering Data in Read-Only Views

### Override list_query

Restrict the data displayed in read-only views:

```python
class RecentOrdersAdmin(ReadOnlyModelView, model=Order):
    name = "Recent Orders"
    
    def list_query(self, request: Request):
        """Show only orders from last 30 days."""
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        return select(Order).where(Order.created_at >= thirty_days_ago)
```

### Filter by User

```python
class MyOrdersAdmin(ReadOnlyModelView, model=Order):
    name = "My Orders"
    
    def list_query(self, request: Request):
        """Show only current user's orders."""
        # Get current user from request (depends on your auth implementation)
        user_id = request.state.user_id
        
        return select(Order).where(Order.user_id == user_id)
    
    def is_accessible(self, request: Request) -> bool:
        """Ensure user is authenticated."""
        return hasattr(request.state, 'user_id')
```

## Computed Columns in Read-Only Views

Display computed values that don't exist in the database:

```python
from sqladmin import ModelView

class OrderSummaryAdmin(ReadOnlyModelView, model=Order):
    column_list = [
        Order.id,
        Order.customer,
        Order.subtotal,
        Order.tax,
        Order.total,
        "profit_margin",  # Computed column
    ]
    
    column_formatters = {
        "profit_margin": lambda m, a: f"{((m.total - m.cost) / m.total * 100):.1f}%"
    }
    
    column_labels = {
        "profit_margin": "Profit Margin"
    }
```

## Permissions and Access Control

Combine read-only views with custom access control:

```python
class SensitiveDataAdmin(ReadOnlyModelView, model=SensitiveData):
    name = "Sensitive Data"
    
    def is_accessible(self, request: Request) -> bool:
        """Only admins can view this data."""
        user = request.state.user
        return user.is_authenticated and user.has_role('admin')
    
    def is_visible(self, request: Request) -> bool:
        """Only show in menu for authorized users."""
        return self.is_accessible(request)
```

## Export-Only Views

Create views where users can only export data:

```python
class DataExportAdmin(ReadOnlyModelView, model=Data):
    name = "Data Export"
    
    can_export = True
    can_view_details = False  # Disable detail view
    
    # Configure export
    export_max_rows = 10000
    export_types = ["csv", "json"]
    
    column_export_list = [
        Data.id,
        Data.field1,
        Data.field2,
        Data.created_at,
    ]
```

## Materialized Views

If you're using PostgreSQL materialized views:

```python
from sqlalchemy import Table, MetaData

metadata = MetaData()

# Define materialized view as a table
sales_summary = Table(
    'sales_summary_mv',
    metadata,
    autoload_with=engine
)

class SalesSummaryAdmin(ReadOnlyModelView):
    # Use table directly
    model = sales_summary
    can_create = False
    can_edit = False
    can_delete = False
```

## Adding Actions to Read-Only Views

Even in read-only views, you can add custom actions:

```python
from sqladmin import action
from starlette.responses import RedirectResponse

class ReportAdmin(ReadOnlyModelView, model=Report):
    @action(
        name="refresh",
        label="Refresh Report",
        confirmation_message="Refresh this report?",
        add_in_detail=True,
        add_in_list=True
    )
    async def refresh_report(self, request: Request):
        """Trigger report regeneration."""
        pks = request.query_params.get("pks", "").split(",")
        
        for pk in pks:
            # Trigger report refresh logic
            await refresh_report_task(pk)
        
        # Redirect back to list
        return RedirectResponse(
            url=request.url_for("admin:list", identity=self.identity),
            status_code=302
        )
```

## Best Practices

### 1. Clear Naming

Use descriptive names that indicate the view is read-only:

```python
class AuditLogAdmin(ReadOnlyModelView, model=AuditLog):
    name = "Audit Log (Read-Only)"
    icon = "fa-solid fa-eye"
```

### 2. Add Helpful Descriptions

Use custom templates to add descriptions:

```html
{% extends "sqladmin/list.html" %}

{% block content_header %}
    <div class="alert alert-info">
        <i class="fa fa-info-circle"></i>
        This is a read-only view. Data cannot be modified through this interface.
    </div>
    {{ super() }}
{% endblock %}
```

### 3. Optimize Queries

Since read-only views often display large datasets:

```python
class LargeDatasetAdmin(ReadOnlyModelView, model=LargeDataset):
    # Increase page size
    page_size = 50
    page_size_options = [25, 50, 100, 200]
    
    # Disable detail view for performance
    can_view_details = False
```

### 4. Use Appropriate Indexes

Ensure database indexes exist for filtered and sorted columns:

```python
class LogEntry(Base):
    __tablename__ = "log_entries"
    
    timestamp = Column(DateTime, index=True)  # Indexed for sorting
    level = Column(String, index=True)  # Indexed for filtering
```

## Complete Example

```python
from datetime import datetime, timedelta
from sqladmin import ModelView
from starlette.requests import Request

class ReadOnlyModelView(ModelView):
    """Base class for all read-only views."""
    can_create = False
    can_edit = False
    can_delete = False
    icon = "fa-solid fa-eye"

class SystemMetricsAdmin(ReadOnlyModelView, model=SystemMetric):
    name = "System Metrics"
    name_plural = "System Metrics"
    
    column_list = [
        SystemMetric.timestamp,
        SystemMetric.cpu_usage,
        SystemMetric.memory_usage,
        SystemMetric.disk_usage,
    ]
    
    column_default_sort = ("timestamp", True)
    
    column_formatters = {
        SystemMetric.cpu_usage: lambda m, a: f"{m.cpu_usage:.1f}%",
        SystemMetric.memory_usage: lambda m, a: f"{m.memory_usage:.1f}%",
        SystemMetric.disk_usage: lambda m, a: f"{m.disk_usage:.1f}%",
    }
    
    def list_query(self, request: Request):
        """Show only last 24 hours of data."""
        yesterday = datetime.now() - timedelta(days=1)
        return select(SystemMetric).where(
            SystemMetric.timestamp >= yesterday
        )
    
    async def perform_list_context(
        self, request: Request, context: dict | None = None
    ) -> dict:
        """Add average metrics to context."""
        context = context or {}
        
        yesterday = datetime.now() - timedelta(days=1)
        
        if self.is_async:
            async with self.session_maker() as session:
                result = await session.execute(
                    select(
                        func.avg(SystemMetric.cpu_usage),
                        func.avg(SystemMetric.memory_usage),
                        func.avg(SystemMetric.disk_usage),
                    ).where(SystemMetric.timestamp >= yesterday)
                )
                avg_cpu, avg_mem, avg_disk = result.one()
        else:
            with self.session_maker() as session:
                result = session.execute(
                    select(
                        func.avg(SystemMetric.cpu_usage),
                        func.avg(SystemMetric.memory_usage),
                        func.avg(SystemMetric.disk_usage),
                    ).where(SystemMetric.timestamp >= yesterday)
                )
                avg_cpu, avg_mem, avg_disk = result.one()
        
        context["avg_cpu"] = f"{avg_cpu:.1f}%"
        context["avg_memory"] = f"{avg_mem:.1f}%"
        context["avg_disk"] = f"{avg_disk:.1f}%"
        
        return context
```

## See Also

- [Model Configuration](../configurations.md)
- [Authentication](../authentication.md)
- [Working with Templates](../working_with_templates.md)

