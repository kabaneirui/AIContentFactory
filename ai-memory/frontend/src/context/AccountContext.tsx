import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api } from "../api/client";
import type { Account } from "../api/types";

interface AccountContextValue {
  accounts: Account[];
  accountId: number | null;
  currentAccount: Account | null;
  setAccountId: (id: number) => void;
  refreshAccounts: () => Promise<void>;
  loading: boolean;
}

const AccountContext = createContext<AccountContextValue | null>(null);

const STORAGE_KEY = "ai-memory-account-id";

export function AccountProvider({ children }: { children: ReactNode }) {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountIdState] = useState<number | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? Number(stored) : null;
  });
  const [loading, setLoading] = useState(true);

  const refreshAccounts = useCallback(async () => {
    const list = await api.listAccounts();
    setAccounts(list);
    if (list.length > 0) {
      setAccountIdState((prev) => {
        if (prev && list.some((a) => a.id === prev)) return prev;
        return list[0].id;
      });
    }
  }, []);

  useEffect(() => {
    refreshAccounts()
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [refreshAccounts]);

  const setAccountId = (id: number) => {
    setAccountIdState(id);
    localStorage.setItem(STORAGE_KEY, String(id));
  };

  const currentAccount = accounts.find((a) => a.id === accountId) ?? null;

  return (
    <AccountContext.Provider
      value={{
        accounts,
        accountId,
        currentAccount,
        setAccountId,
        refreshAccounts,
        loading,
      }}
    >
      {children}
    </AccountContext.Provider>
  );
}

export function useAccount() {
  const ctx = useContext(AccountContext);
  if (!ctx) throw new Error("useAccount must be used within AccountProvider");
  return ctx;
}
