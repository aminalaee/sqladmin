"""FastAPI demo application with SQLAdmin showcasing all features."""

import uvicorn
from admin_views import (
    CategoryAdmin,
    DepartmentAdmin,
    OrderAdmin,
    OrderItemAdmin,
    OrderReportAdmin,
    ProductAdmin,
    RoleAdmin,
    TagAdmin,
    UserAdmin,
)
from fastapi import FastAPI
from models import engine, init_db

from sqladmin import Admin

# Create FastAPI app
app = FastAPI(
    title="SQLAdmin Demo",
    description="Demo application showcasing all SQLAdmin features",
    version="1.0.0",
)

# Initialize database
init_db()

# Create admin
admin = Admin(
    app,
    engine,
    title="SQLAdmin Demo - All Features",
    logo_url="https://raw.githubusercontent.com/aminalaee/sqladmin/main/docs/assets/images/banner.png",
)

# Add views in logical order
admin.add_view(UserAdmin)
admin.add_view(DepartmentAdmin)
admin.add_view(RoleAdmin)
admin.add_view(ProductAdmin)
admin.add_view(CategoryAdmin)
admin.add_view(TagAdmin)
admin.add_view(OrderAdmin)
admin.add_view(OrderItemAdmin)
admin.add_view(OrderReportAdmin)  # Read-only report view


@app.get("/")
async def root():
    return {
        "message": "SQLAdmin Demo Application",
        "admin_url": "/admin",
        "features": [
            "UniqueValuesFilter with Integer/Float support",
            "ManyToManyFilter for junction tables",
            "RelatedModelFilter for related model columns",
            "DateRangeFilter with datetime inputs",
            "Enhanced ForeignKeyFilter with multiple selection",
            "Pretty export (CSV & JSON)",
            "Custom actions",
            "Read-only views",
            "Async search support",
        ],
    }


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 SQLAdmin Demo Application")
    print("=" * 60)
    print("\n📍 URLs:")
    print("   Main:  http://localhost:8000")
    print("   Admin: http://localhost:8000/admin")
    print("\n✨ Features to test:")
    print("   • UniqueValuesFilter - Users (age, salary)")
    print("   • ManyToManyFilter - Users by Role")
    print("   • RelatedModelFilter - Orders by Customer Department")
    print("   • DateRangeFilter - Users/Orders/Products by date")
    print("   • Pretty Export - CSV & JSON with formatting")
    print("   • Custom Actions - Activate Users")
    print("   • Read-only View - Order Reports")
    print("\n" + "=" * 60)
    print()

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
