import { UserProvider } from "./context/UserContext";
import { AppRouter } from "./AppRouter";

export default function App() {
  return (
    <UserProvider>
      <AppRouter />
    </UserProvider>
  );
}