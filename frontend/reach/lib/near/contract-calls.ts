import type { WalletSelector } from "@near-wallet-selector/core";

const REACH_CONTRACT = "reach.testnet";
const STABLECOIN_CONTRACT = "usdc.fakes.testnet";

export async function createTaskOnChain(
  selector: WalletSelector,
  accountId: string,
  budget: number, // whole units, e.g. naira-pegged stablecoin amount
  desc: string,
  tag: string | null,
  decimals: number // stablecoin decimals — need this from you
) {
  const wallet = await selector.wallet();
  const amount = BigInt(Math.round(budget * 10 ** decimals)).toString();

  await wallet.signAndSendTransaction({
    receiverId: STABLECOIN_CONTRACT,
    actions: [
      {
        type: "FunctionCall",
        params: {
          methodName: "ft_transfer_call",
          args: {
            receiver_id: REACH_CONTRACT,
            amount,
            msg: JSON.stringify({
              CreateTask: {
                desc,
                tag,
                stablecoin: STABLECOIN_CONTRACT,
                terms: {
                  labor_fee: amount,
                  material_cost: "0",
                  upfront_release_pct: 0,
                  required_provider_collateral: null,
                },
              },
            }),
          },
          gas: "100000000000000",
          deposit: "1", // 1 yoctoNEAR required by ft_transfer_call
        },
      },
    ],
  });
}

export async function createApplicationOnChain(selector: WalletSelector, taskId: number) {
  const wallet = await selector.wallet();
  await wallet.signAndSendTransaction({
    receiverId: REACH_CONTRACT,
    actions: [
      {
        type: "FunctionCall",
        params: {
          methodName: "create_application",
          args: { task_id: taskId },
          gas: "30000000000000",
          deposit: "0",
        },
      },
    ],
  });
}

export async function acceptApplicationOnChain(selector: WalletSelector, nearApplicationId: number) {
  const wallet = await selector.wallet();
  await wallet.signAndSendTransaction({
    receiverId: REACH_CONTRACT,
    actions: [
      {
        type: "FunctionCall",
        params: {
          methodName: "accept_application",
          args: { application_id: nearApplicationId },
          gas: "50000000000000",
          deposit: "0",
        },
      },
    ],
  });
}

export async function approveWorkOnChain(selector: WalletSelector, nearTaskId: number) {
  const wallet = await selector.wallet();
  await wallet.signAndSendTransaction({
    receiverId: REACH_CONTRACT,
    actions: [
      {
        type: "FunctionCall",
        params: {
          methodName: "approve_work",
          args: { task_id: nearTaskId },
          gas: "50000000000000",
          deposit: "0",
        },
      },
    ],
  });
}

export async function completeTaskOnChain(selector: WalletSelector, nearTaskId: number) {
  const wallet = await selector.wallet();
  await wallet.signAndSendTransaction({
    receiverId: REACH_CONTRACT,
    actions: [
      {
        type: "FunctionCall",
        params: {
          methodName: "complete_task",
          args: { task_id: nearTaskId },
          gas: "30000000000000",
          deposit: "0",
        },
      },
    ],
  });
}