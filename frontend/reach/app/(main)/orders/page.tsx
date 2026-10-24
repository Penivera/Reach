"use client";

import { useState } from "react";
import OrderItem, { OrderStatus } from "@/components/ui/OrderItem";
import Button from "@/components/ui/Button";
import { releaseJobPayment } from "@/lib/payment";
import { toast } from "@/lib/toast";

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

const initialMockOrders: Order[] = [
  {
    id: "ord_1",
    productId: "rice-5kg",
    businessName: "Mama Beatrice",
    productName: "5kg Local Rice",
    productSubtext: "Lekki Market",
    price: "₦4,500",
    orderedAt: "July 2, 2026",
    status: "escrow-active",
  },
  {
    id: "ord_2",
    productId: "plumber-service",
    businessName: "Abiola (Plumber)",
    productName: "Kitchen Sink Leakage Fix",
    price: "₦5,000",
    orderedAt: "July 2, 2026",
    status: "escrow-active",
  },
  {
    id: "ord_3",
    productId: "stylist",
    businessName: "Kemi (Stylist)",
    productName: "Braid Extensions",
    price: "₦3,500",
    orderedAt: "June 28, 2026",
    status: "escrow-released",
  },
  {
    id: "ord_4",
    productId: "tailor",
    businessName: "Chidi (Tailor)",
    productName: "Ankara Dress Custom Stitch",
    price: "₦6,000",
    orderedAt: "June 20, 2026",
    status: "under-dispute",
  },
];

function EmptyOrders() {
  return (
    <div className="flex flex-col items-center justify-center rounded-[20px] border border-dashed border-stroke px-6 py-16 text-center mt-4">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-shade">
        <svg
          viewBox="0 0 24 24"
          className="h-7 w-7 text-muted-foreground"
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
      <p className="text-[16px] font-bold text-foreground">No orders yet</p>
      <p className="mt-1.5 max-w-xs text-[14px] font-medium text-muted-foreground">
        Once you request something, it'll show up here so you can track it.
      </p>
      <div className="mt-6 w-full max-w-50">
        <Button href="/browse" className="w-full rounded-[14px]">Start browsing</Button>
      </div>
    </div>
  );
}

export default function OrdersPage() {

  // const [activeOrders, setActiveOrders] = useState<Order[]>(initialMockOrders);
  const [activeOrders, setActiveOrders] = useState<Order[]>([]);

  async function handleRelease(orderId: string) {
    if (!window.confirm("Are you sure you want to release these funds to the provider? This action cannot be undone.")) {
      return;
    }

    try {
      if (orderId.startsWith("ord_")) {
        await new Promise((resolve) => setTimeout(resolve, 600)); // Simulate network latency
      } else {
        await releaseJobPayment(orderId);
      }

      // INSTANT UI UPDATE: Mutate state to change status to "escrow-released"
      setActiveOrders((prevOrders) =>
        prevOrders.map((order) =>
          order.id === orderId ? { ...order, status: "escrow-released" } : order
        )
      );

      toast.success("Funds released! Order is now completed.");
    } catch (error) {
      console.error("Release failed:", error);
    }
  }

  return (
    <div className="min-h-screen bg-background px-5 py-6 pb-30">
      <h1 className="text-[28px] font-bold text-foreground tracking-tight">My Orders</h1>

      <div className="mt-6 flex flex-col gap-4">
        {activeOrders.length === 0 ? (
          <EmptyOrders />
        ) : (
          activeOrders.map((order) => (
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