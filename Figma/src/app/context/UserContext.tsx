import { createContext, useContext, useState, ReactNode } from "react";

interface UserContextType {
  userId: number | null;
  userName: string | null;
  setUser: (userId: number, userName: string) => void;
  logout: () => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  // Lectura sincrona (lazy init) para que el usuario ya este disponible en el
  // primer render — evita un ciclo de render "sin usuario" que retrasaba
  // todas las cargas de datos de las paginas.
  const [userId, setUserId] = useState<number | null>(() => {
    const saved = localStorage.getItem("athleteUserId");
    return saved ? parseInt(saved) : null;
  });
  const [userName, setUserName] = useState<string | null>(() => {
    return localStorage.getItem("athleteUserName");
  });

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
