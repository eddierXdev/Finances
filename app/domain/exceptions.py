"""Domain-level exceptions."""


class DomainError(Exception):
    """Base class for business rule violations."""


class CurrencyMismatchError(DomainError):
    """Raised when two monetary values use different currencies."""


class AccountCurrencyMismatchError(CurrencyMismatchError):
    """Raised when an account cannot operate in the requested currency."""


class InvalidExchangeRateError(DomainError):
    """Raised when an exchange rate violates domain rules."""


class CurrencyNotFoundError(DomainError):
    """Raised when a referenced currency is not registered."""


class ImmutableExchangeRateError(DomainError):
    """Raised when an attempt is made to modify a historical exchange rate."""


class DuplicateSkuError(DomainError):
    """Raised when a SKU is already assigned to another variant."""


class CategoryNotFoundError(DomainError):
    """Raised when a referenced category does not exist."""


class ProductNotFoundError(DomainError):
    """Raised when a referenced product does not exist."""


class VariantNotFoundError(DomainError):
    """Raised when a referenced product variant does not exist."""


class AttributeNotFoundError(DomainError):
    """Raised when a referenced attribute does not exist."""


class AttributeValueNotFoundError(DomainError):
    """Raised when a referenced attribute value does not exist."""


class AccountNotFoundError(DomainError):
    """Raised when a referenced account does not exist."""


class InactiveAccountError(DomainError):
    """Raised when an operation targets an inactive account."""


class ExchangeRateNotFoundError(DomainError):
    """Raised when a referenced exchange rate does not exist."""


class StaleExchangeRateError(DomainError):
    """Raised when a stored rate is older than the allowed freshness window."""


class InvalidLedgerEntryError(DomainError):
    """Raised when a financial transaction violates ledger rules."""


class InvalidTransferError(DomainError):
    """Raised when an account transfer violates transfer rules."""


class InvalidExpenseError(DomainError):
    """Raised when an expense violates a business rule."""


class ExpenseNotFoundError(DomainError):
    """Raised when a referenced expense does not exist."""


class SupplierNotFoundError(DomainError):
    """Raised when a referenced supplier does not exist."""


class PurchaseNotFoundError(DomainError):
    """Raised when a referenced purchase does not exist."""


class PurchaseItemNotFoundError(DomainError):
    """Raised when a referenced purchase item does not exist."""


class PurchaseCostNotFoundError(DomainError):
    """Raised when a referenced purchase cost does not exist."""


class PurchaseCurrencyMismatchError(CurrencyMismatchError):
    """Raised when purchase data uses a currency other than its own."""


class InvalidPurchaseError(DomainError):
    """Raised when a purchase violates business rules."""


class InvalidPurchaseTransitionError(InvalidPurchaseError):
    """Raised when a purchase status transition is not allowed."""


class PurchasePaymentError(InvalidPurchaseError):
    """Raised when full payment cannot be registered for a purchase."""


class InvalidCostAllocationError(DomainError):
    """Raised when a purchase cost cannot be allocated correctly."""


class InvalidInventoryError(DomainError):
    """Raised when inventory data violates a business rule."""


class InsufficientStockError(InvalidInventoryError):
    """Raised when a lot does not have enough remaining quantity."""


class OverReceiptError(InvalidInventoryError):
    """Raised when a receipt exceeds the ordered quantity."""


class InvalidInventoryMovementError(InvalidInventoryError):
    """Raised when an inventory movement violates sign or data rules."""


class InventoryLotNotFoundError(InvalidInventoryError):
    """Raised when a referenced inventory lot does not exist."""


class InvalidSaleError(DomainError):
    """Raised when a sale violates a business rule."""


class SaleCurrencyMismatchError(CurrencyMismatchError):
    """Raised when sale data uses a currency other than its own."""


class InvalidSaleTransitionError(InvalidSaleError):
    """Raised when a sale status transition is not allowed."""


class SaleNotFoundError(DomainError):
    """Raised when a referenced sale does not exist."""


class SaleItemNotFoundError(DomainError):
    """Raised when a referenced sale item does not exist."""


class SaleItemLotAllocationNotFoundError(DomainError):
    """Raised when a referenced FIFO allocation does not exist."""


class CustomerNotFoundError(DomainError):
    """Raised when a referenced customer does not exist."""


class InvalidCustomerReturnError(DomainError):
    """Raised when a customer return violates a business rule."""


class ExcessReturnError(InvalidCustomerReturnError):
    """Raised when a return exceeds the net quantity sold."""


class CustomerRefundError(InvalidCustomerReturnError):
    """Raised when a customer refund violates a business rule."""


class CustomerReturnNotFoundError(DomainError):
    """Raised when a referenced customer return does not exist."""


class CustomerReturnItemNotFoundError(DomainError):
    """Raised when a referenced customer return item does not exist."""


class ReturnLotAllocationNotFoundError(DomainError):
    """Raised when a referenced return lot allocation does not exist."""


class InvalidSupplierReturnError(DomainError):
    """Raised when a supplier return violates a business rule."""


class InvalidSupplierReturnLotError(InvalidSupplierReturnError):
    """Raised when a lot does not belong to the returned purchase item."""


class ExcessSupplierReturnError(InvalidSupplierReturnError):
    """Raised when a supplier return exceeds the lot's remaining stock."""


class SupplierRefundError(InvalidSupplierReturnError):
    """Raised when a supplier refund violates a business rule."""


class SupplierReturnNotFoundError(DomainError):
    """Raised when a referenced supplier return does not exist."""


class SupplierReturnItemNotFoundError(DomainError):
    """Raised when a referenced supplier return item does not exist."""
