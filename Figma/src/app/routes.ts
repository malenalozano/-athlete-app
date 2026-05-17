import { createBrowserRouter } from "react-router";
import { Home } from "./pages/Home";
import { Profile } from "./pages/Profile";
import { PersonalTrainer } from "./pages/PersonalTrainer";
import { CicloMenstrual } from "./pages/CicloMenstrual";
import { Calendario } from "./pages/Calendario";
import { PlanSemanal } from "./pages/PlanSemanal";
import { Diario } from "./pages/Diario";
import { Ejercicios } from "./pages/Ejercicios";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Home,
  },
  {
    path: "/plan-semanal",
    Component: PlanSemanal,
  },
  {
    path: "/diario",
    Component: Diario,
  },
  {
    path: "/calendario",
    Component: Calendario,
  },
  {
    path: "/perfil",
    Component: Profile,
  },
  {
    path: "/ejercicios",
    Component: Ejercicios,
  },
  {
    path: "/entrenador",
    Component: PersonalTrainer,
  },
  {
    path: "/ciclo-menstrual",
    Component: CicloMenstrual,
  },
]);
