# Advanced Filtering

This guide demonstrates advanced filtering capabilities in SQLAdmin.

## Overview

SQLAdmin provides several powerful filter types for complex data filtering scenarios:

- **UniqueValuesFilter** - Filter by unique column values with support for numeric types
- **ManyToManyFilter** - Filter through many-to-many relationships
- **RelatedModelFilter** - Filter by columns in related models
- **ForeignKeyFilter** - Filter by foreign key relationships
- **BooleanFilter** - Filter boolean columns
- **StaticValuesFilter** - Filter with predefined static values
- **OperationColumnFilter** - Universal filter with multiple operations

## UniqueValuesFilter

Enhanced filter for unique column values with support for Integer, Float types, custom sorting, and value formatting.

### Basic Usage

```python
from sqladmin import ModelView
from sqladmin.filters import UniqueValuesFilter

class UserAdmin(ModelView, model=User):
    column_filters = [
        UniqueValuesFilter(User.status),
        UniqueValuesFilter(User.age),
    ]
```

### Advanced Features

#### Custom Sorting

```python
UniqueValuesFilter(
    User.name,
    lookups_order=User.name.desc()  # Sort lookups in descending order
)
```

#### Float Value Formatting

```python
import math

UniqueValuesFilter(
    Product.price,
    lookups_ui_method=lambda value: f"${value:.2f}",  # Display as "$10.99"
    float_round_method=lambda value: math.floor(value)  # Round down for filtering
)
```

#### Integer Values

```python
UniqueValuesFilter(
    Order.quantity,
    title="Order Quantity",
    parameter_name="qty"
)
```

## ManyToManyFilter

Filter through many-to-many relationships using a link table.

### Example: Users and Roles

```python
from sqladmin.filters import ManyToManyFilter

# Model definitions
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String)

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)

# Filter configuration
class UserAdmin(ModelView, model=User):
    column_filters = [
        ManyToManyFilter(
            column=User.id,
            link_model=UserRole,
            local_field="user_id",
            foreign_field="role_id",
            foreign_model=Role,
            foreign_display_field=Role.name,
            title="Role",
            lookups_order=Role.name  # Sort roles alphabetically
        )
    ]
```

### Example: Posts and Tags

```python
class PostAdmin(ModelView, model=Post):
    column_filters = [
        ManyToManyFilter(
            column=Post.id,
            link_model=PostTag,
            local_field="post_id",
            foreign_field="tag_id",
            foreign_model=Tag,
            foreign_display_field=Tag.name,
            title="Tags"
        )
    ]
```

## RelatedModelFilter

Filter by columns in related models through JOIN operations.

### Example: Filter Users by City

```python
from sqladmin.filters import RelatedModelFilter

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    address_id = Column(Integer, ForeignKey("addresses.id"))
    address = relationship("Address")

class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True)
    city = Column(String)
    country = Column(String)

class UserAdmin(ModelView, model=User):
    column_filters = [
        RelatedModelFilter(
            column=User.address,  # Relationship for joining
            foreign_column=Address.city,  # Column to filter by
            foreign_model=Address,
            title="City",
            lookups_order=Address.city
        ),
        RelatedModelFilter(
            column=User.address,
            foreign_column=Address.country,
            foreign_model=Address,
            title="Country"
        )
    ]
```

### Filter by Boolean in Related Model

```python
class OrderAdmin(ModelView, model=Order):
    column_filters = [
        RelatedModelFilter(
            column=Order.customer,
            foreign_column=Customer.is_active,
            foreign_model=Customer,
            title="Active Customers Only"
        )
    ]
```

## ForeignKeyFilter

Enhanced foreign key filter with support for multiple values and custom ordering.

### Basic Usage

```python
from sqladmin.filters import ForeignKeyFilter

class ProductAdmin(ModelView, model=Product):
    column_filters = [
        ForeignKeyFilter(
            foreign_key=Product.category_id,
            foreign_display_field=Category.name,
            foreign_model=Category,
            title="Category",
            lookups_order=Category.name  # Sort categories alphabetically
        )
    ]
```

### Multiple Selection Support

The enhanced `ForeignKeyFilter` now supports selecting multiple values:

```python
# Users can now select multiple categories in the filter UI
ForeignKeyFilter(
    foreign_key=Product.category_id,
    foreign_display_field=Category.name,
    foreign_model=Category
)
```

## DateRangeFilter

Filter by date or datetime ranges with start and end values.

### Basic Usage

```python
from sqladmin.filters import DateRangeFilter

class OrderAdmin(ModelView, model=Order):
    column_filters = [
        DateRangeFilter(
            Order.created_at,
            title="Created Date"
        ),
        DateRangeFilter(
            Order.shipped_at,
            title="Shipped Date"
        )
    ]
```

### How It Works

The `DateRangeFilter` allows users to filter by a date/datetime range:
- Users can specify start date, end date, or both
- Supports both `date` and `datetime` column types
- Automatically parses ISO format date strings

### Usage in List View

In the admin interface, users will see input fields for start and end dates.
The filter will apply based on what they provide:

- **Both dates**: Shows records between start and end (inclusive)
- **Start only**: Shows records from start date onwards
- **End only**: Shows records up to end date

## Combining Multiple Filters

You can combine different filter types for powerful filtering:

```python
class OrderAdmin(ModelView, model=Order):
    column_filters = [
        # Filter by customer
        ForeignKeyFilter(
            foreign_key=Order.customer_id,
            foreign_display_field=Customer.name,
            foreign_model=Customer,
            lookups_order=Customer.name
        ),
        
        # Filter by order status
        UniqueValuesFilter(
            Order.status,
            title="Status"
        ),
        
        # Filter by product tags (many-to-many)
        ManyToManyFilter(
            column=Order.id,
            link_model=OrderProduct,
            local_field="order_id",
            foreign_field="product_id",
            foreign_model=Product,
            foreign_display_field=Product.name,
            title="Products"
        ),
        
        # Filter by shipping city
        RelatedModelFilter(
            column=Order.shipping_address,
            foreign_column=Address.city,
            foreign_model=Address,
            title="Shipping City"
        ),
        
        # Filter by total amount
        UniqueValuesFilter(
            Order.total_amount,
            lookups_ui_method=lambda value: f"${value:.2f}"
        ),
        
        # Filter by date range
        DateRangeFilter(
            Order.created_at,
            title="Order Date"
        )
    ]
```

## Custom Filter Parameters

All filters support custom parameters:

```python
UniqueValuesFilter(
    User.status,
    title="Account Status",  # Display name in UI
    parameter_name="status"  # URL parameter name
)
```

## Best Practices

### 1. Use Appropriate Filter Types

- **UniqueValuesFilter**: For columns with a reasonable number of unique values (< 1000)
- **ManyToManyFilter**: For filtering through junction tables
- **RelatedModelFilter**: For filtering by related model attributes
- **ForeignKeyFilter**: For foreign key relationships

### 2. Add Sorting for Better UX

```python
UniqueValuesFilter(
    Product.name,
    lookups_order=Product.name  # Alphabetical order
)
```

### 3. Use Meaningful Titles

```python
RelatedModelFilter(
    column=Order.customer,
    foreign_column=Customer.email,
    foreign_model=Customer,
    title="Customer Email"  # Clear and descriptive
)
```

### 4. Format Numeric Values

```python
UniqueValuesFilter(
    Product.price,
    lookups_ui_method=lambda value: f"${value:,.2f}",  # $1,234.56
    float_round_method=lambda value: math.floor(value)
)
```

## Performance Considerations

### Index Your Filter Columns

```python
class User(Base):
    __tablename__ = "users"
    status = Column(String, index=True)  # Add index for filtered columns
    created_at = Column(DateTime, index=True)
```

### Limit Lookup Values

For columns with many unique values, consider using `StaticValuesFilter` instead:

```python
from sqladmin.filters import StaticValuesFilter

StaticValuesFilter(
    User.status,
    values=[
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("pending", "Pending")
    ]
)
```

### Use Relationship Loading

When using `RelatedModelFilter`, ensure relationships are properly configured:

```python
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.name, "address.city"]
    
    column_filters = [
        RelatedModelFilter(
            column=User.address,
            foreign_column=Address.city,
            foreign_model=Address
        )
    ]
```

## See Also

- [Model Configuration](../configurations.md)
- [Working with Templates](../working_with_templates.md)
- [API Reference - ModelView](../api_reference/model_view.md)

