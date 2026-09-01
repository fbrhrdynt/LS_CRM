"""Pydantic models for LogiSource entities. All ids are string UUIDs."""
from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- USERS ----------
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: Literal["admin", "staff"] = "staff"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[Literal["admin", "staff"]] = None
    password: Optional[str] = None


class UserOut(UserBase):
    id: str
    created_at: str
    updated_at: str


# ---------- AUTH ----------
class LoginIn(BaseModel):
    email: EmailStr
    password: str
    remember: bool = False


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


# ---------- CUSTOMERS ----------
class CustomerBase(BaseModel):
    company_name: str
    pic_name: Optional[str] = ""
    position: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    website: Optional[str] = ""
    notes: Optional[str] = ""


class CustomerCreate(CustomerBase):
    code: Optional[str] = None


class CustomerUpdate(BaseModel):
    company_name: Optional[str] = None
    pic_name: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None


# ---------- PRODUCTS ----------
class ProductBase(BaseModel):
    name: str
    product_type: Literal["goods", "service"] = "goods"
    category: Optional[str] = ""
    brand: Optional[str] = ""
    description: Optional[str] = ""
    unit: Optional[str] = "pcs"
    selling_price: float = 0
    purchase_price: float = 0
    tax_percent: float = 0
    status: Literal["active", "inactive"] = "active"
    # Goods specific
    sku: Optional[str] = ""
    stock: Optional[int] = 0
    warranty: Optional[str] = ""
    # Service specific
    sla: Optional[str] = ""
    duration: Optional[str] = ""
    support_period: Optional[str] = ""


class ProductCreate(ProductBase):
    code: Optional[str] = None


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None
    product_type: Optional[Literal["goods", "service"]] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    selling_price: Optional[float] = None
    purchase_price: Optional[float] = None
    tax_percent: Optional[float] = None
    status: Optional[Literal["active", "inactive"]] = None
    sku: Optional[str] = None
    stock: Optional[int] = None
    warranty: Optional[str] = None
    sla: Optional[str] = None
    duration: Optional[str] = None
    support_period: Optional[str] = None


# ---------- CATEGORIES ----------
class CategoryIn(BaseModel):
    name: str


# ---------- QUOTATION / INVOICE LINE ITEMS ----------
class LineItem(BaseModel):
    product_id: Optional[str] = ""
    product_name: str
    description: Optional[str] = ""
    quantity: float = 1
    unit_price: float = 0
    discount_percent: float = 0
    tax_percent: float = 0

    @property
    def line_total(self) -> float:
        subtotal = self.quantity * self.unit_price
        after_discount = subtotal * (1 - self.discount_percent / 100)
        return after_discount * (1 + self.tax_percent / 100)


class QuotationBase(BaseModel):
    customer_id: str
    date: str  # ISO date
    valid_until: Optional[str] = ""
    currency: str = "IDR"
    items: List[LineItem] = []
    notes: Optional[str] = ""
    payment_terms: Optional[str] = ""
    delivery_time: Optional[str] = ""


class QuotationCreate(QuotationBase):
    status: Literal["draft", "sent", "approved", "rejected"] = "draft"


class QuotationUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    customer_id: Optional[str] = None
    date: Optional[str] = None
    valid_until: Optional[str] = None
    currency: Optional[str] = None
    items: Optional[List[LineItem]] = None
    notes: Optional[str] = None
    payment_terms: Optional[str] = None
    delivery_time: Optional[str] = None
    status: Optional[Literal["draft", "sent", "approved", "rejected"]] = None


# ---------- INVOICES ----------
class InvoiceBase(BaseModel):
    customer_id: str
    quotation_id: Optional[str] = ""
    date: str
    due_date: Optional[str] = ""
    currency: str = "IDR"
    items: List[LineItem] = []
    notes: Optional[str] = ""
    payment_terms: Optional[str] = ""


class InvoiceCreate(InvoiceBase):
    status: Literal["draft", "unpaid", "partial", "paid", "cancelled"] = "unpaid"
    paid_amount: float = 0


class InvoiceUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    customer_id: Optional[str] = None
    date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    items: Optional[List[LineItem]] = None
    notes: Optional[str] = None
    payment_terms: Optional[str] = None
    status: Optional[Literal["draft", "unpaid", "partial", "paid", "cancelled"]] = None
    paid_amount: Optional[float] = None


# ---------- PROJECTS ----------
class ProjectBase(BaseModel):
    name: str
    customer_id: str
    start_date: Optional[str] = ""
    end_date: Optional[str] = ""
    description: Optional[str] = ""
    status: Literal["planning", "progress", "completed", "maintenance", "closed"] = "planning"
    product_ids: List[str] = []
    account_ids: List[str] = []
    license_ids: List[str] = []


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None
    customer_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["planning", "progress", "completed", "maintenance", "closed"]] = None
    product_ids: Optional[List[str]] = None
    account_ids: Optional[List[str]] = None
    license_ids: Optional[List[str]] = None


# ---------- ACCOUNTS (VAULT) ----------
class AccountBase(BaseModel):
    name: str
    category: str = "Custom"
    customer_id: Optional[str] = ""
    project_id: Optional[str] = ""
    username: Optional[str] = ""
    email: Optional[str] = ""
    password: Optional[str] = ""  # plaintext incoming; server encrypts
    login_url: Optional[str] = ""
    recovery_email: Optional[str] = ""
    recovery_phone: Optional[str] = ""
    registration_number: Optional[str] = ""
    license_key: Optional[str] = ""
    subscription_id: Optional[str] = ""
    api_key: Optional[str] = ""
    secret_key: Optional[str] = ""
    expiry_date: Optional[str] = ""
    renewal_date: Optional[str] = ""
    notes: Optional[str] = ""


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None
    category: Optional[str] = None
    customer_id: Optional[str] = None
    project_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    login_url: Optional[str] = None
    recovery_email: Optional[str] = None
    recovery_phone: Optional[str] = None
    registration_number: Optional[str] = None
    license_key: Optional[str] = None
    subscription_id: Optional[str] = None
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    expiry_date: Optional[str] = None
    renewal_date: Optional[str] = None
    notes: Optional[str] = None


# ---------- LICENSES ----------
class LicenseBase(BaseModel):
    product_id: Optional[str] = ""
    product_name: Optional[str] = ""
    customer_id: Optional[str] = ""
    registration_number: Optional[str] = ""
    license_code: Optional[str] = ""
    expiry_date: Optional[str] = ""
    renewal_date: Optional[str] = ""
    notes: Optional[str] = ""


class LicenseCreate(LicenseBase):
    pass


class LicenseUpdate(LicenseBase):
    pass


# ---------- SETTINGS ----------
class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    company_name: Optional[str] = None
    company_tagline: Optional[str] = None
    company_logo_url: Optional[str] = None
    company_email: Optional[str] = None
    company_phone: Optional[str] = None
    company_address: Optional[str] = None
    currency: Optional[str] = None
    tax_percent: Optional[float] = None
    quotation_prefix: Optional[str] = None
    invoice_prefix: Optional[str] = None
    project_prefix: Optional[str] = None
