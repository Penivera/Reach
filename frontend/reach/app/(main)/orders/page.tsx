"use client";

import OrderItem, { OrderStatus } from "@/components/ui/OrderItem";
import Button from "@/components/ui/Button";

interface Order {
  id: string;
  productId: string;
  businessName: string;
  productName: string;
  productSubtext?: string;
  price: string | number;
  orderedAt: string;
  status: OrderStatus;
}

const orders: Order[] = [
  {
    id: "ord_1",
    productId: "rice-5kg",
    businessName: "Mama Tani Foods",
    productName: "Local rice, 5kg",
    price: "₦4,500",
    orderedAt: "2 hours ago",
    status: "escrow-active",
  },
  {
    id: "ord_2",
    productId: "generator-service",
    businessName: "Emeka Electricals",
    productName: "Generator repair",
    productSubtext: "Home visit",
    price: "₦8,000",
    orderedAt: "Yesterday",
    status: "escrow-released",
  },
  {
    id: "ord_3",
    productId: "phone-case",
    businessName: "Uyo Gadgets",
    productName: "Phone case",
    price: "₦1,200",
    orderedAt: "3 days ago",
    status: "under-dispute",
  },
];

function EmptyOrders() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-stroke px-6 py-16 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-shade">
        <svg
          viewBox="0 0 24 24"
          className="h-6 w-6 text-muted-foreground"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M4 7h16l-1.5 12.5a2 2 0 0 1-2 1.5H7.5a2 2 0 0 1-2-1.5L4 7Z" />
          <path d="M9 7V5a3 3 0 0 1 6 0v2" />
        </svg>
      </div>
      <p className="text-sm font-semibold text-foreground">No orders yet</p>
      <p className="mt-1 max-w-xs text-sm text-muted-foreground">
        Once you request something, it'll show up here so you can track it.
      </p>
      <div className="mt-4">
        <Button href="/browse">Start browsing</Button>
      </div>
    </div>
  );
}

function handleRelease(orderId: string) {
  // TODO: wire up the real escrow-release call — this probably wants a
  // confirm step before it fires, given it's moving money.
  console.log("release", orderId);
}

export default function OrdersPage() {
  return (
    <div className="min-h-screen bg-background px-4 py-6">
      <h1 className="text-lg font-semibold text-foreground">My orders</h1>

      <div className="mt-4 flex flex-col gap-3">
        {orders.length === 0 ? (
          <EmptyOrders />
        ) : (
          orders.map((order) => (
            <OrderItem
              key={order.id}
              businessName={order.businessName}
              productName={order.productName}
              productSubtext={order.productSubtext}
              price={order.price}
              orderedAt={order.orderedAt}
              status={order.status}
              trackHref={`/orders/${order.id}/track`}
              onRelease={() => handleRelease(order.id)}
              reorderHref={`/product/${order.productId}`}
            />
          ))
        )}
      </div>
    </div>
  );
}