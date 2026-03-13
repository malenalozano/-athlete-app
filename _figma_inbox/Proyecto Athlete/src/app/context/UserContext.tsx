import { createContext, useContext, useState, ReactNode, useEffect } from "react";

interface UserContextType {
  userId: number | null;
  userName: string | null;
  setUser: (userId: number, userName: string) => void;
  logout: () => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState<number | null>(null);
  const [userName, setUserName] = useState<string | null>(null);

  // Cargar usuario guardado del localStorage
  useEffect(() => {
    const savedUserId = localStorage.getItem("athleteUserId");
    const savedUserName = localStorage.getItem("athleteUserName");
    
    if (savedUserId && savedUserName) {
      setUserId(parseInt(savedUserId));
      setUserName(savedUserName);
    }
  }, []);

  const setUser = (id: number, name: string) => {
    setUserId(id);
    setUserName(name);
    localStorage.setItem("athleteUserId", id.toString());
    localStorage.setItem("athleteUserName", name);
  };

  const logout = () => {
    setUserId(null);
    setUserName(null);
    localStorage.removeItem("athleteUserId");
    localStorage.removeItem("athleteUserName");
  };

  return (
    <UserContext.Provider value={{ userId, userName, setUser, logout }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return context;
}
