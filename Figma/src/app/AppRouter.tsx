import { useUser } from "./context/UserContext";
import { Login } from "./pages/Login";
import { RouterProvider } from "react-router";
import { router } from "./routes";

export function AppRouter() {
  const { userId, setUser } = useUser();

  // Si no hay usuario, mostrar pantalla de login
  if (!userId) {
    return <Login onSelectUser={setUser} />;
  }

  // Si hay usuario, mostrar app principal
  return <RouterProvider router={router} />;
}
