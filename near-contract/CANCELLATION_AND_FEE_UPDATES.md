# Cancellation Methods & Fee Structure

This document outlines the design and implementation of the centralized fee structure, task cancellation methods, and provider abandonment mechanics in the Reach Task-Escrow contract.

## 1. Fee Structure
* **Basis Points (BPS):** Fees are represented as basis points (where `100` = 1%, `1,000` = 10%, and `10,000` = 100% maximum). These are configured via the state variables `creation_fee_pct` and `cancellation_fee_pct` on `ReachContract`.
* **Centralized Calculation:** All fees are processed through a centralized method:
  ```rust
  pub(crate) fn calculate_fee(&self, amount: u128, fee_basis_points: u16) -> u128;
  ```
* **Creation Fee (On Top):** Debited during task creation. When a creator launches a task requiring a $100 escrow under a 2.5% creation fee (`creation_fee_pct = 250`), they are debited $102.50. The task vault receives the active $100 escrow (`creator_locked_balance`), while the remaining $2.50 is immediately credited to the protocol's fee balance.
* **Cancellation Fee (Deducted):** Subtracted from the creator's active locked escrow when a task is canceled.

---

## 2. Cancel Task (`cancel_task`)
* **Authorized Caller:** The Task Creator.
* **Timing/Conditions:** Allowed only if the task status is `Pending` (no provider assigned yet) or `AwaitingEscrow` (provider accepted but hasn't successfully locked collateral yet). It is **not** allowed once the task reaches `InProgress`.
* **Resolution Mechanics:**
  1. The cancellation fee (default 10%, i.e., `1,000` basis points, adjustable by admins) is calculated on the creator's locked escrow and added to the protocol's fee balance.
  2. The remaining escrow is returned to the creator.
  3. Task status transitions to `Refunded`.

---

## 3. Cancel Approved Application (`cancel_approved_application`)
* **Authorized Caller:** The assigned Provider (effectively abandoning the task).
* **Timing/Conditions:** Allowed when the task is in `InProgress` or `AwaitingEscrow` state.
* **Resolution Mechanics:** Matches the upfront material advance received against the provider's locked collateral:

### Case A: Upfront Advance ≤ Collateral
* **Action:** Provider calls `cancel_approved_application` directly.
* **Refund:** The provider is refunded their locked collateral minus the advance they kept (`collateral - advance`).
* **Reset:** The task status resets back to `Pending` (Open) so a new provider can apply. The creator's active escrow remains fully intact.
* **History:** The application's status is set to `Rejected`.

### Case B: Upfront Advance > Collateral
* **Action:** Provider initiates the cancellation via an FT transfer call (`ft_transfer_call`) sending the required debt payload to the contract.
* **Refund:** The provider receives 0 collateral refund.
* **Payback:** The provider pays back the difference to the task vault (`advance - collateral`) in the same transaction.
* **Abandonment Penalty:** The provider pays a 10% fee (changeable by admins) calculated on the task's value, which is sent directly to the protocol fee vault. The total amount the provider must transfer is `(advance - collateral) + fee`.
* **Reset:** The task status resets back to `Pending` (Open), restoring the creator's active escrow.
* **History & Penalty:** The application's status transitions to `CancelledWithDebt` to record the abandonment, and the provider's account is permanently blacklisted.

---

## 4. Blacklist Enforcement
* When a provider incurs debt via a Case B application cancellation, their `AccountId` is added to the contract's `blacklist` set.
* The contract checks the blacklist during `create_application`. Any blacklisted provider is immediately barred from applying to any future tasks.
