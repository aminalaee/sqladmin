"""Admin view configurations showcasing all sqladmin features."""

import math

from models import (
    Category,
    Department,
    Order,
    OrderItem,
    Product,
    Role,
    Tag,
    User,
    product_tag_table,
    user_role_table,
)
from starlette.requests import Request
from starlette.responses import RedirectResponse

from sqladmin import ModelView, action
from sqladmin.filters import (
    BooleanFilter,
    DateRangeFilter,
    ForeignKeyFilter,
    ManyToManyFilter,
    RelatedModelFilter,
    UniqueValuesFilter,
)


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"

    # List page configuration
    column_list = [
        User.id,
        User.name,
        User.email,
        User.age,
        User.salary,
        User.is_active,
        "department.name",
    ]
    column_searchable_list = [User.name, User.email]
    column_sortable_list = [
        User.name,
        User.email,
        User.age,
        User.salary,
        User.created_at,
    ]
    column_default_sort = ("created_at", True)

    # Showcase ALL filter types
    column_filters = [
        # BooleanFilter
        BooleanFilter(User.is_active, title="Active Status"),
        # UniqueValuesFilter with Integer
        UniqueValuesFilter(User.age, title="Age", lookups_order=User.age),
        # UniqueValuesFilter with Float and custom formatting
        UniqueValuesFilter(
            User.salary,
            title="Salary",
            lookups_ui_method=lambda v: f"${v:,.2f}",
            float_round_method=lambda v: math.floor(v / 10000) * 10000,  # Round to 10k
            lookups_order=User.salary,
        ),
        # ForeignKeyFilter with ordering
        ForeignKeyFilter(
            User.department_id,
            Department.name,
            foreign_model=Department,
            title="Department",
            lookups_order=Department.name,
        ),
        # ManyToManyFilter
        ManyToManyFilter(
            column=User.id,
            link_model=user_role_table,
            local_field="user_id",
            foreign_field="role_id",
            foreign_model=Role,
            foreign_display_field=Role.name,
            title="Role",
            lookups_order=Role.name,
        ),
        # DateRangeFilter
        DateRangeFilter(User.created_at, title="Registration Date"),
    ]

    # Details page
    column_details_list = [
        User.id,
        User.name,
        User.email,
        User.age,
        User.salary,
        User.is_active,
        User.created_at,
        "department.name",
        "roles",
    ]

    # Export configuration
    can_export = True
    export_types = ["csv", "json"]
    use_pretty_export = True

    column_export_list = [
        User.id,
        User.name,
        User.email,
        User.age,
        User.salary,
        "department.name",
    ]

    column_labels = {
        User.email: "Email Address",
        "department.name": "Department",
    }

    column_formatters = {
        User.salary: lambda m, a: f"${m.salary:,.2f}",
        User.created_at: lambda m, a: m.created_at.strftime("%Y-%m-%d %H:%M"),
    }

    # Custom action
    @action(
        name="activate_users",
        label="Activate Selected Users",
        confirmation_message="Are you sure you want to activate selected users?",
        add_in_list=True,
        add_in_detail=False,
    )
    async def activate_users(self, request: Request):
        pks = request.query_params.get("pks", "").split(",")
        for pk in pks:
            if pk:
                user = await self.get_object_for_edit(request)
                if user:
                    # In real app, you'd update the user here
                    pass

        return RedirectResponse(
            url=request.url_for("admin:list", identity=self.identity), status_code=302
        )


class DepartmentAdmin(ModelView, model=Department):
    name = "Department"
    name_plural = "Departments"
    icon = "fa-solid fa-building"

    column_list = [Department.id, Department.name, Department.budget]
    column_sortable_list = [Department.name, Department.budget]

    column_filters = [
        UniqueValuesFilter(
            Department.budget,
            lookups_ui_method=lambda v: f"${v:,.0f}",
            lookups_order=Department.budget,
        )
    ]

    column_formatters = {
        Department.budget: lambda m, a: f"${m.budget:,.2f}",
    }


class RoleAdmin(ModelView, model=Role):
    name = "Role"
    name_plural = "Roles"
    icon = "fa-solid fa-shield"

    column_list = [Role.id, Role.name, Role.description]
    column_searchable_list = [Role.name]


class ProductAdmin(ModelView, model=Product):
    name = "Product"
    name_plural = "Products"
    icon = "fa-solid fa-box"

    column_list = [
        Product.id,
        Product.name,
        Product.price,
        Product.stock,
        Product.is_available,
        "category.name",
    ]

    column_searchable_list = [Product.name, Product.description]
    column_sortable_list = [
        Product.name,
        Product.price,
        Product.stock,
        Product.created_at,
    ]
    column_default_sort = ("created_at", True)

    # Showcase multiple advanced filters
    column_filters = [
        BooleanFilter(Product.is_available, title="Available"),
        UniqueValuesFilter(
            Product.price,
            title="Price Range",
            lookups_ui_method=lambda v: f"${v:.2f}",
            float_round_method=lambda v: math.floor(v / 10) * 10,  # Round to $10
        ),
        UniqueValuesFilter(Product.stock, title="Stock Level"),
        ForeignKeyFilter(
            Product.category_id,
            Category.name,
            foreign_model=Category,
            lookups_order=Category.name,
        ),
        ManyToManyFilter(
            column=Product.id,
            link_model=product_tag_table,
            local_field="product_id",
            foreign_field="tag_id",
            foreign_model=Tag,
            foreign_display_field=Tag.name,
            title="Tags",
            lookups_order=Tag.name,
        ),
        DateRangeFilter(Product.created_at, title="Created Date"),
    ]

    column_formatters = {
        Product.price: lambda m, a: f"${m.price:.2f}",
        Product.stock: lambda m, a: f"{m.stock} units",
    }

    column_formatters_detail = {
        Product.price: lambda m, a: f"${m.price:.2f}",
        Product.created_at: lambda m, a: m.created_at.strftime("%Y-%m-%d"),
    }

    use_pretty_export = True
    export_types = ["csv", "json"]


class CategoryAdmin(ModelView, model=Category):
    name = "Category"
    name_plural = "Categories"
    icon = "fa-solid fa-folder"

    column_list = [Category.id, Category.name]


class TagAdmin(ModelView, model=Tag):
    name = "Tag"
    name_plural = "Tags"
    icon = "fa-solid fa-tag"

    column_list = [Tag.id, Tag.name]


class OrderAdmin(ModelView, model=Order):
    name = "Order"
    name_plural = "Orders"
    icon = "fa-solid fa-shopping-cart"

    column_list = [
        Order.id,
        Order.order_number,
        "user.name",
        Order.total_amount,
        Order.status,
        Order.created_at,
    ]

    column_searchable_list = [Order.order_number]
    column_sortable_list = [Order.order_number, Order.total_amount, Order.created_at]
    column_default_sort = ("created_at", True)

    # Multiple filters showcase
    column_filters = [
        UniqueValuesFilter(Order.status, title="Order Status"),
        ForeignKeyFilter(
            Order.user_id, User.name, foreign_model=User, lookups_order=User.name
        ),
        # RelatedModelFilter - filter by user's department
        RelatedModelFilter(
            column=Order.user,
            foreign_column=Department.name,
            foreign_model=Department,
            title="Customer Department",
        ),
        DateRangeFilter(Order.created_at, title="Order Date"),
        DateRangeFilter(Order.shipped_at, title="Shipped Date"),
    ]

    column_formatters = {
        Order.total_amount: lambda m, a: f"${m.total_amount:.2f}",
        Order.created_at: lambda m, a: m.created_at.strftime("%Y-%m-%d %H:%M"),
    }

    use_pretty_export = True


class OrderItemAdmin(ModelView, model=OrderItem):
    name = "Order Item"
    name_plural = "Order Items"
    icon = "fa-solid fa-list"

    column_list = [
        OrderItem.id,
        "order.order_number",
        "product.name",
        OrderItem.quantity,
        OrderItem.price,
    ]

    column_formatters = {
        OrderItem.price: lambda m, a: f"${m.price:.2f}",
    }


# Read-only view example
class OrderReportAdmin(ModelView, model=Order):
    name = "Order Report"
    name_plural = "Order Reports"
    icon = "fa-solid fa-chart-bar"
    category = "Reports"

    # Read-only
    can_create = False
    can_edit = False
    can_delete = False
    can_export = True

    column_list = [
        Order.order_number,
        "user.name",
        Order.total_amount,
        Order.status,
        Order.created_at,
    ]

    column_filters = [
        DateRangeFilter(Order.created_at, title="Date Range"),
        UniqueValuesFilter(Order.status),
    ]

    column_formatters = {
        Order.total_amount: lambda m, a: f"${m.total_amount:,.2f}",
    }

    use_pretty_export = True
    export_types = ["csv", "json"]
