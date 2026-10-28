"""Return application use cases."""

from app.application.returns.register_customer_return import (
    CustomerReturnItemRequest,
    RegisteredCustomerReturn,
    RegisterCustomerReturn,
    RegisterCustomerReturnRequest,
)
from app.application.returns.register_supplier_return import (
    RegisteredSupplierReturn,
    RegisterSupplierReturn,
    RegisterSupplierReturnRequest,
    SupplierReturnItemRequest,
)

__all__ = [
    "CustomerReturnItemRequest",
    "RegisterCustomerReturn",
    "RegisterCustomerReturnRequest",
    "RegisteredCustomerReturn",
    "RegisterSupplierReturn",
    "RegisterSupplierReturnRequest",
    "RegisteredSupplierReturn",
    "SupplierReturnItemRequest",
]
