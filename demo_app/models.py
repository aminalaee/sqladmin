"""Database models for demo application."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# Association tables for many-to-many relationships
user_role_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)

product_tag_table = Table(
    "product_tags",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    age: Mapped[int] = mapped_column(Integer)
    salary: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Foreign key
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )

    # Relationships
    department: Mapped[Optional["Department"]] = relationship(back_populates="users")
    roles: Mapped[List["Role"]] = relationship(
        secondary=user_role_table, back_populates="users"
    )
    orders: Mapped[List["Order"]] = relationship(back_populates="user")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    budget: Mapped[float] = mapped_column(Float)

    users: Mapped[List["User"]] = relationship(back_populates="department")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    users: Mapped[List["User"]] = relationship(
        secondary=user_role_table, back_populates="roles"
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    price: Mapped[float] = mapped_column(Float)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )

    category: Mapped[Optional["Category"]] = relationship(back_populates="products")
    tags: Mapped[List["Tag"]] = relationship(
        secondary=product_tag_table, back_populates="products"
    )
    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="product")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

    products: Mapped[List["Product"]] = relationship(back_populates="category")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))

    products: Mapped[List["Product"]] = relationship(
        secondary=product_tag_table, back_populates="tags"
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True)
    total_amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    user: Mapped["User"] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="order_items")


# Create engine
engine = create_engine(
    "sqlite:///demo.db",
    connect_args={"check_same_thread": False},
    echo=False,  # Set to True for SQL debugging
)


def init_db():
    """Initialize database with tables and sample data."""
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        # Check if data already exists
        if session.query(Department).first():
            print("Database already initialized")
            return

        # Create departments
        dept_it = Department(name="IT", budget=500000.0)
        dept_hr = Department(name="HR", budget=200000.0)
        dept_sales = Department(name="Sales", budget=300000.0)
        session.add_all([dept_it, dept_hr, dept_sales])

        # Create roles
        role_admin = Role(name="Admin", description="System administrator")
        role_user = Role(name="User", description="Regular user")
        role_manager = Role(name="Manager", description="Department manager")
        session.add_all([role_admin, role_user, role_manager])

        # Create categories
        cat_electronics = Category(name="Electronics")
        cat_books = Category(name="Books")
        cat_clothing = Category(name="Clothing")
        session.add_all([cat_electronics, cat_books, cat_clothing])

        # Create tags
        tag_new = Tag(name="New")
        tag_sale = Tag(name="Sale")
        tag_popular = Tag(name="Popular")
        session.add_all([tag_new, tag_sale, tag_popular])

        session.commit()

        # Create users
        user1 = User(
            name="Alice Johnson",
            email="alice@example.com",
            age=28,
            salary=75000.5,
            is_active=True,
            department_id=dept_it.id,
            created_at=datetime(2024, 1, 15, 10, 30),
        )
        user1.roles.append(role_admin)
        user1.roles.append(role_user)

        user2 = User(
            name="Bob Smith",
            email="bob@example.com",
            age=35,
            salary=85000.75,
            is_active=True,
            department_id=dept_it.id,
            created_at=datetime(2024, 3, 20, 14, 15),
        )
        user2.roles.append(role_manager)

        user3 = User(
            name="Charlie Brown",
            email="charlie@example.com",
            age=42,
            salary=95000.0,
            is_active=False,
            department_id=dept_hr.id,
            created_at=datetime(2024, 6, 10, 9, 0),
        )
        user3.roles.append(role_user)

        user4 = User(
            name="Diana Prince",
            email="diana@example.com",
            age=30,
            salary=80000.0,
            is_active=True,
            department_id=dept_sales.id,
            created_at=datetime(2024, 9, 5, 11, 45),
        )
        user4.roles.append(role_manager)
        user4.roles.append(role_user)

        session.add_all([user1, user2, user3, user4])
        session.commit()

        # Create products
        products = [
            Product(
                name="Laptop Pro 15",
                description="High-performance laptop",
                price=1299.99,
                stock=15,
                is_available=True,
                category_id=cat_electronics.id,
                created_at=datetime(2024, 2, 1),
            ),
            Product(
                name="Python Programming Book",
                description="Learn Python from scratch",
                price=49.99,
                stock=100,
                is_available=True,
                category_id=cat_books.id,
                created_at=datetime(2024, 3, 15),
            ),
            Product(
                name="T-Shirt Blue",
                description="Cotton blue t-shirt",
                price=19.99,
                stock=50,
                is_available=True,
                category_id=cat_clothing.id,
                created_at=datetime(2024, 5, 20),
            ),
            Product(
                name="Wireless Mouse",
                description="Ergonomic wireless mouse",
                price=29.99,
                stock=0,
                is_available=False,
                category_id=cat_electronics.id,
                created_at=datetime(2024, 7, 10),
            ),
        ]

        products[0].tags.extend([tag_new, tag_popular])
        products[1].tags.append(tag_popular)
        products[2].tags.append(tag_sale)
        products[3].tags.append(tag_sale)

        session.add_all(products)
        session.commit()

        # Create orders
        order1 = Order(
            order_number="ORD-2024-001",
            total_amount=1349.98,
            status="completed",
            user_id=user1.id,
            created_at=datetime(2024, 4, 1, 10, 0),
            shipped_at=datetime(2024, 4, 3, 14, 30),
        )

        order2 = Order(
            order_number="ORD-2024-002",
            total_amount=99.97,
            status="processing",
            user_id=user2.id,
            created_at=datetime(2024, 8, 15, 11, 30),
        )

        order3 = Order(
            order_number="ORD-2024-003",
            total_amount=49.99,
            status="pending",
            user_id=user4.id,
            created_at=datetime(2024, 11, 20, 15, 45),
        )

        session.add_all([order1, order2, order3])
        session.commit()

        # Create order items
        items = [
            OrderItem(
                order_id=order1.id, product_id=products[0].id, quantity=1, price=1299.99
            ),
            OrderItem(
                order_id=order1.id, product_id=products[1].id, quantity=1, price=49.99
            ),
            OrderItem(
                order_id=order2.id, product_id=products[2].id, quantity=5, price=19.99
            ),
            OrderItem(
                order_id=order3.id, product_id=products[1].id, quantity=1, price=49.99
            ),
        ]

        session.add_all(items)
        session.commit()

        print("✅ Database initialized with sample data!")


if __name__ == "__main__":
    init_db()
