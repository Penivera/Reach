"use client";

import { setupWalletSelector } from "@near-wallet-selector/core";
import type { WalletSelector } from "@near-wallet-selector/core";
import { setupModal } from "@near-wallet-selector/modal-ui";
import { setupMyNearWallet } from "@near-wallet-selector/my-near-wallet";
import { setupMeteorWallet } from "@near-wallet-selector/meteor-wallet";

let selectorInstance: WalletSelector | null = null;
let modalInstance: ReturnType<typeof setupModal> | null = null;

export async function getWalletSelector() {
  if (selectorInstance) return selectorInstance;

  selectorInstance = await setupWalletSelector({
    network: "testnet",
    modules: [setupMyNearWallet(), setupMeteorWallet()],
  });

  modalInstance = setupModal(selectorInstance, {
    contractId: "reach.testnet",
  });

  return selectorInstance;
}

export function getWalletModal() {
  if (!modalInstance) throw new Error("Call getWalletSelector() first");
  return modalInstance;
}