import { providers } from "near-api-js";

const provider = new providers.JsonRpcProvider({ url: "https://rpc.testnet.near.org" });

export async function viewMethod<T>(methodName: string, args: object): Promise<T> {
  const res: any = await provider.query({
    request_type: "call_function",
    account_id: "reach.testnet",
    method_name: methodName,
    args_base64: Buffer.from(JSON.stringify(args)).toString("base64"),
    finality: "final",
  });
  return JSON.parse(Buffer.from(res.result).toString());
}

export async function getNearTaskId(creatorId: string): Promise<number> {
  const tasks: [number, unknown][] = await viewMethod("get_tasks_by_creator", {
    creator_id: creatorId,
    from_index: 0,
    limit: 100,
  });
  if (tasks.length === 0) throw new Error("No task found for creator");
  return tasks.reduce((max, cur) => (cur[0] > max[0] ? cur : max))[0];
}

export async function getNearApplicationId(taskId: number, providerId: string): Promise<number> {
  const apps: [number, { provider_id: string }][] = await viewMethod("get_applications_by_task", {
    task_id: taskId,
  });
  const mine = apps.filter(([, a]) => a.provider_id === providerId);
  if (mine.length === 0) throw new Error("No application found for provider on this task");
  return mine.reduce((max, cur) => (cur[0] > max[0] ? cur : max))[0];
}